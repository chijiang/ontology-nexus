'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
    Box,
    Zap,
    Settings,
    Trash2,
    GripVertical,
    Plus,
    Repeat,
    Code,
    ShieldCheck,
    Wand2,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { dataProductsApi, DataProduct, GrpcServiceSchema, GrpcMethodInfo } from '@/lib/api';
import { Loader2, ExternalLink } from 'lucide-react';

// --- Types ---

export interface SchemaNode {
    name: string;
    label: string;
    dataProperties: string[];
}

export interface SchemaRelationship {
    source: string;
    type: string;
    target: string;
}

export interface Schema {
    nodes: SchemaNode[];
    relationships: SchemaRelationship[];
}

export type BlockType = 'SET' | 'TRIGGER' | 'FOR' | 'PRECONDITION' | 'CALL';

export interface LogicBlockData {
    id: string;
    type: BlockType;
    target?: string;
    value?: string;
    actionEntity?: string;
    actionName?: string;
    variable?: string;
    entity?: string;
    conditions?: string;
    label?: string; // For PRECONDITION
    onFailure?: string; // For PRECONDITION
    dataProduct?: string; // For CALL
    methodName?: string; // For CALL
    args?: { name: string; value: string }[]; // For CALL
    children?: LogicBlockData[];
}

interface BusinessEditorProps {
    mode: 'RULE' | 'ACTION';
    initialDsl?: string;
    onDslChange: (dsl: string) => void;
    schema: Schema;
    meta: {
        name: string;
        priority?: number;
        trigger?: {
            type: string;
            entity: string;
            property: string | null;
        };
        entityType?: string; // For ACTION
        description?: string; // For ACTION
        parameters?: { name: string; type: string; optional: boolean }[]; // For ACTION
    };
}

// --- Helper Functions for Tree State ---

const updateNodeInTree = (nodes: LogicBlockData[], id: string, field: string, value: any): LogicBlockData[] => {
    return nodes.map((node) => {
        if (node.id === id) {
            return { ...node, [field]: value };
        }
        if (node.children) {
            return { ...node, children: updateNodeInTree(node.children, id, field, value) };
        }
        return node;
    });
};

const removeNodeFromTree = (nodes: LogicBlockData[], id: string): LogicBlockData[] => {
    return nodes
        .filter((node) => node.id !== id)
        .map((node) => {
            if (node.children) {
                return { ...node, children: removeNodeFromTree(node.children, id) };
            }
            return node;
        });
};

const addNodeToTree = (nodes: LogicBlockData[], parentId: string | null, newNode: LogicBlockData): LogicBlockData[] => {
    if (parentId === null) {
        return [...nodes, newNode];
    }
    return nodes.map((node) => {
        if (node.id === parentId) {
            return { ...node, children: [...(node.children || []), newNode] };
        }
        if (node.children) {
            return { ...node, children: addNodeToTree(node.children, parentId, newNode) };
        }
        return node;
    });
};

const reorderNodesInTree = (nodes: LogicBlockData[], activeId: string, overId: string): LogicBlockData[] => {
    const activeIndex = nodes.findIndex((n) => n.id === activeId);
    const overIndex = nodes.findIndex((n) => n.id === overId);

    if (activeIndex !== -1 && overIndex !== -1) {
        return arrayMove(nodes, activeIndex, overIndex);
    }

    return nodes.map((node) => {
        if (node.children) {
            return { ...node, children: reorderNodesInTree(node.children, activeId, overId) };
        }
        return node;
    });
};

// --- DSL Parser ---

const parseDslToBlocks = (dsl: string, mode: 'RULE' | 'ACTION'): { statements: LogicBlockData[], preconditions: LogicBlockData[] } => {
    const statements: LogicBlockData[] = [];
    const preconditions: LogicBlockData[] = [];

    if (!dsl) return { statements, preconditions };

    const lines = dsl.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('//'));

    // Stack for handling nested blocks (FOR)
    const stack: LogicBlockData[][] = [statements];
    let isInEffect = mode === 'RULE'; // Rules don't have EFFECT wrapper, Actions do.

    lines.forEach((line, index) => {
        // Description (Action only)
        if (mode === 'ACTION' && line.startsWith('DESCRIPTION:')) {
            // Description is usually handled in the parent component or via meta,
            // but we can extract it if needed. However, meta is usually passed from outside.
            return;
        }

        // Preconditions (Action only)
        if (mode === 'ACTION' && line.startsWith('PRECONDITION')) {
            const match = line.match(/PRECONDITION\s+(\w+):\s*(.*)/);
            if (match) {
                const onFailureMatch = lines[lines.indexOf(line) + 1]?.match(/ON_FAILURE:\s*"(.*)"/);
                preconditions.push({
                    id: Math.random().toString(36).substr(2, 9),
                    type: 'PRECONDITION',
                    label: match[1],
                    conditions: match[2].trim(),
                    onFailure: onFailureMatch ? onFailureMatch[1] : undefined
                });
            }
            return;
        }
        if (line.startsWith('ON_FAILURE')) return; // Handled by lookahead

        // Effect Wrapper (Action only)
        if (mode === 'ACTION' && line.startsWith('EFFECT')) {
            isInEffect = true;
            return;
        }

        if (!isInEffect) return;

        // SET
        if (line.startsWith('SET')) {
            const match = line.match(/SET\s+([^=]+)\s*=\s*(.*);/);
            if (match) {
                stack[stack.length - 1].push({
                    id: Math.random().toString(36).substr(2, 9),
                    type: 'SET',
                    target: match[1].trim(),
                    value: match[2].trim().replace(/;$/, '')
                });
            }
        }
        // TRIGGER
        else if (line.startsWith('TRIGGER')) {
            const match = line.match(/TRIGGER\s+([\w.]+)\s+ON\s+(.*);/);
            if (match) {
                const parts = match[1].split('.');
                stack[stack.length - 1].push({
                    id: Math.random().toString(36).substr(2, 9),
                    type: 'TRIGGER',
                    actionEntity: parts[0],
                    actionName: parts[1] || '',
                    target: match[2].trim().replace(/;$/, '')
                });
            }
        }
        // FOR
        else if (line.startsWith('FOR')) {
            const match = line.match(/FOR\s*\(([^:]+):\s*(\w+)(?:\s+WHERE\s+(.*))?\)\s*\{/);
            if (match) {
                const newBlock: LogicBlockData = {
                    id: Math.random().toString(36).substr(2, 9),
                    type: 'FOR',
                    variable: match[1].trim(),
                    entity: match[2].trim(),
                    conditions: match[3] ? match[3].trim() : '',
                    children: []
                };
                stack[stack.length - 1].push(newBlock);
                stack.push(newBlock.children!);
            }
        }
        // CALL
        else if (line.startsWith('CALL')) {
            const match = line.match(/CALL\s+(?:"([^"]+)"|([\w.]+))\.([\w.]+)\s*\(\s*{?(.*?)}?\s*\);/);
            if (match) {
                const productName = match[1] || match[2];
                const methodName = match[3];
                const argsStr = match[4];
                const args: { name: string; value: string }[] = [];
                if (argsStr.trim()) {
                    const argParts = argsStr.split(',').map(p => p.trim());
                    argParts.forEach(p => {
                        const [name, ...valParts] = p.split(':').map(x => x.trim());
                        if (name && valParts.length > 0) {
                            args.push({ name, value: valParts.join(':').trim() });
                        }
                    });
                }
                stack[stack.length - 1].push({
                    id: Math.random().toString(36).substr(2, 9),
                    type: 'CALL',
                    dataProduct: productName,
                    methodName: methodName,
                    args: args
                });
            }
        }
        // End of Block
        else if (line === '}') {
            if (stack.length > 1) {
                stack.pop();
            }
        }
    });

    return { statements, preconditions };
};

export const parseActionSignature = (dsl: string): { entityType: string, actionName: string, parameters: { name: string; type: string; optional: boolean }[] } | null => {
    const lines = dsl.split('\n');
    const actionLine = lines.find(l => l.trim().startsWith('ACTION'));
    if (!actionLine) return null;

    const match = actionLine.match(/ACTION\s+([\w.]+)\s*(?:\((.*)\))?\s*\{/);
    if (!match) return null;

    const fullPath = match[1];
    const [entityType, actionName] = fullPath.split('.');
    const paramsStr = match[2];
    const parameters: { name: string; type: string; optional: boolean }[] = [];

    if (paramsStr) {
        const paramParts = paramsStr.split(',').map(p => p.trim());
        paramParts.forEach(p => {
            const pMatch = p.match(/(\w+):\s*(\w+)(\?)?/);
            if (pMatch) {
                parameters.push({
                    name: pMatch[1],
                    type: pMatch[2],
                    optional: !!pMatch[3]
                });
            }
        });
    }

    return { entityType, actionName, parameters };
};

// --- Components ---

const LogicBlock = ({
    id,
    data,
    updateStatement,
    removeStatement,
    addStatement,
    schema,
}: {
    id: string;
    data: LogicBlockData;
    updateStatement: (id: string, field: string, value: any) => void;
    removeStatement: (id: string) => void;
    addStatement: (parentId: string | null, type: BlockType) => void;
    schema: Schema;
}) => {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 50 : 'auto',
        opacity: isDragging ? 0.5 : 1,
    };

    const isLoop = data.type === 'FOR';
    const isPrecondition = data.type === 'PRECONDITION';

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`relative flex flex-col items-start gap-2 p-3 bg-white border rounded-lg shadow-sm group mb-3 transition-colors ${isLoop ? 'border-indigo-200 bg-indigo-50/30' :
                isPrecondition ? 'border-emerald-200 bg-emerald-50/30' :
                    'border-slate-200 hover:border-blue-400'
                }`}
        >
            <div className="flex items-start w-full gap-3">
                {/* Drag Handle */}
                {!isPrecondition && (
                    <div {...attributes} {...listeners} className="mt-2 text-slate-300 cursor-grab hover:text-slate-500 flex-shrink-0">
                        <GripVertical size={16} />
                    </div>
                )}

                {/* Content Body */}
                <div className="flex-1 w-full">
                    {/* Header Line */}
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase flex-shrink-0 ${data.type === 'SET' ? 'bg-amber-100 text-amber-700' :
                                data.type === 'TRIGGER' ? 'bg-purple-100 text-purple-700' :
                                    data.type === 'PRECONDITION' ? 'bg-emerald-100 text-emerald-700' :
                                        'bg-indigo-100 text-indigo-700'
                                }`}
                        >
                            {data.type}
                        </span>

                        {data.type === 'SET' && (
                            <>
                                <input
                                    type="text"
                                    value={data.target || ''}
                                    onChange={(e) => updateStatement(id, 'target', e.target.value)}
                                    placeholder="entity.prop"
                                    className="px-2 py-1 border border-slate-200 rounded w-32 text-slate-700 focus:border-blue-500 outline-none font-mono text-xs bg-white"
                                />
                                <span className="text-slate-400 text-xs">=</span>
                                <input
                                    type="text"
                                    value={data.value || ''}
                                    onChange={(e) => updateStatement(id, 'value', e.target.value)}
                                    placeholder="val"
                                    className="flex-1 min-w-[100px] px-2 py-1 border border-slate-200 rounded text-slate-700 focus:border-blue-500 outline-none font-mono text-xs bg-white"
                                />
                            </>
                        )}

                        {data.type === 'PRECONDITION' && (
                            <div className="flex flex-col gap-2 flex-1">
                                <div className="flex items-center gap-2">
                                    <input
                                        type="text"
                                        value={data.label || ''}
                                        onChange={(e) => updateStatement(id, 'label', e.target.value)}
                                        placeholder="name"
                                        className="px-2 py-1 border border-slate-200 rounded w-24 text-slate-700 focus:border-emerald-500 outline-none font-mono text-xs bg-white"
                                    />
                                    <span className="text-slate-400 text-xs">:</span>
                                    <input
                                        type="text"
                                        value={data.conditions || ''}
                                        onChange={(e) => updateStatement(id, 'conditions', e.target.value)}
                                        placeholder="expression"
                                        className="flex-1 min-w-[150px] px-2 py-1 border border-slate-200 rounded text-slate-700 focus:border-emerald-500 outline-none font-mono text-xs bg-white"
                                    />
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-slate-400 text-[10px] uppercase font-bold flex-shrink-0">Failure Message:</span>
                                    <input
                                        type="text"
                                        value={data.onFailure || ''}
                                        onChange={(e) => updateStatement(id, 'onFailure', e.target.value)}
                                        placeholder="Describe the error if this check fails..."
                                        className="flex-1 px-2 py-1 border border-slate-200 rounded text-slate-700 focus:border-emerald-500 outline-none text-xs bg-white italic"
                                    />
                                </div>
                            </div>
                        )}

                        {data.type === 'TRIGGER' && (
                            <>
                                <select
                                    value={data.actionEntity || ''}
                                    onChange={(e) => updateStatement(id, 'actionEntity', e.target.value)}
                                    className="px-2 py-1 border border-slate-200 rounded text-slate-700 outline-none text-xs bg-white w-32"
                                >
                                    <option value="">Entity Type</option>
                                    {schema.nodes.map((n) => (
                                        <option key={n.name} value={n.name}>
                                            {n.name}
                                        </option>
                                    ))}
                                </select>
                                <span className="text-slate-400">.</span>
                                <input
                                    type="text"
                                    value={data.actionName || ''}
                                    onChange={(e) => updateStatement(id, 'actionName', e.target.value)}
                                    placeholder="action"
                                    className="px-2 py-1 border border-slate-200 rounded text-slate-700 focus:border-blue-500 outline-none font-mono text-xs bg-white w-24"
                                />
                                <span className="text-slate-500 text-xs font-mono">ON</span>
                                <input
                                    type="text"
                                    value={data.target || ''}
                                    onChange={(e) => updateStatement(id, 'target', e.target.value)}
                                    placeholder="var"
                                    className="w-20 px-2 py-1 border border-slate-200 rounded text-slate-700 focus:border-blue-500 outline-none font-mono text-xs bg-white"
                                />
                            </>
                        )}

                        {data.type === 'FOR' && (
                            <>
                                <div className="flex items-center bg-white border border-indigo-200 rounded px-2 py-1 shadow-sm">
                                    <input
                                        className="w-6 text-center text-xs font-bold text-indigo-700 outline-none border-b border-indigo-100 focus:border-indigo-500 bg-transparent"
                                        value={data.variable || ''}
                                        onChange={(e) => updateStatement(id, 'variable', e.target.value)}
                                        placeholder="v"
                                    />
                                    <span className="mx-1 text-slate-400 text-xs">:</span>
                                    <select
                                        value={data.entity || ''}
                                        onChange={(e) => updateStatement(id, 'entity', e.target.value)}
                                        className="text-xs font-semibold text-indigo-700 outline-none bg-transparent"
                                    >
                                        <option value="">Entity</option>
                                        {schema.nodes.map((n) => (
                                            <option key={n.name} value={n.name}>
                                                {n.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <span className="text-xs font-medium text-slate-500 uppercase">WHERE</span>
                                <input
                                    className="flex-1 min-w-[150px] bg-white border border-slate-200 rounded px-2 py-1 text-xs font-mono text-slate-600 outline-none focus:border-indigo-500"
                                    value={data.conditions || ''}
                                    onChange={(e) => updateStatement(id, 'conditions', e.target.value)}
                                    placeholder="e.g. v.amount > 100"
                                />
                            </>
                        )}

                        {data.type === 'CALL' && (
                            <CallBlockConfig
                                data={data}
                                updateStatement={(field, value) => updateStatement(id, field, value)}
                            />
                        )}
                    </div>

                    {/* Recursive Children Container */}
                    {isLoop && (
                        <div className="pl-4 border-l-2 border-indigo-200 ml-1 mt-2">
                            <div className="flex flex-col gap-2 min-h-[20px] pt-1 pb-1">
                                <SortableContext items={(data.children || []).map(c => c.id)} strategy={verticalListSortingStrategy}>
                                    {data.children?.map((child) => (
                                        <LogicBlock
                                            key={child.id}
                                            id={child.id}
                                            data={child}
                                            updateStatement={updateStatement}
                                            removeStatement={removeStatement}
                                            addStatement={addStatement}
                                            schema={schema}
                                        />
                                    ))}
                                </SortableContext>

                                {(!data.children || data.children.length === 0) && (
                                    <div className="text-[10px] text-slate-400 italic py-1">
                                        Empty loop. Add logic below.
                                    </div>
                                )}
                            </div>

                            {/* Nested Add Buttons */}
                            <div className="flex gap-2 mt-2 pt-2 border-t border-indigo-100 border-dashed">
                                <button
                                    onClick={() => addStatement(id, 'SET')}
                                    className="text-[10px] flex items-center gap-1 px-1.5 py-0.5 bg-white border border-slate-200 rounded hover:border-indigo-500 text-slate-600 transition-colors"
                                >
                                    <Plus size={10} /> Set
                                </button>
                                <button
                                    onClick={() => addStatement(id, 'TRIGGER')}
                                    className="text-[10px] flex items-center gap-1 px-1.5 py-0.5 bg-white border border-slate-200 rounded hover:border-indigo-500 text-slate-600 transition-colors"
                                >
                                    <Plus size={10} /> Trigger
                                </button>
                                <button
                                    onClick={() => addStatement(id, 'FOR')}
                                    className="text-[10px] flex items-center gap-1 px-1.5 py-0.5 bg-white border border-slate-200 rounded hover:border-indigo-500 text-slate-600 transition-colors"
                                >
                                    <Plus size={10} /> Loop
                                </button>
                                <button
                                    onClick={() => addStatement(id, 'CALL')}
                                    className="text-[10px] flex items-center gap-1 px-1.5 py-0.5 bg-white border border-slate-200 rounded hover:border-indigo-500 text-slate-600 transition-colors"
                                >
                                    <Plus size={10} /> Call
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Delete Button */}
                <button
                    onClick={() => removeStatement(id)}
                    className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors flex-shrink-0"
                >
                    <Trash2 size={14} />
                </button>
            </div>
        </div>
    );
};

// --- Sub-component for CALL configuration ---
const CallBlockConfig = ({ data, updateStatement }: { data: LogicBlockData, updateStatement: (field: string, value: any) => void }) => {
    const [products, setProducts] = useState<DataProduct[]>([]);
    const [schema, setSchema] = useState<GrpcServiceSchema | null>(null);
    const [loading, setLoading] = useState(false);
    const [isManual, setIsManual] = useState(false);

    useEffect(() => {
        const fetchProducts = async () => {
            try {
                const res = await dataProductsApi.list(true);
                setProducts(res.data.items);
            } catch (err) {
                console.error('Failed to fetch data products', err);
            }
        };
        fetchProducts();
    }, []);

    useEffect(() => {
        const fetchSchema = async () => {
            if (!data.dataProduct) return;
            const product = products.find(p => p.name === data.dataProduct);
            if (!product) return;

            setLoading(true);
            try {
                const res = await dataProductsApi.getSchema(product.id);
                setSchema(res.data);
            } catch (err) {
                console.error('Failed to fetch schema', err);
            } finally {
                setLoading(false);
            }
        };
        fetchSchema();
    }, [data.dataProduct, products]);

    const activeMethod = useMemo(() => {
        return schema?.methods.find(m => m.name === data.methodName);
    }, [schema, data.methodName]);

    const methodParams = useMemo(() => {
        if (!activeMethod || !schema) return [];
        const inputType = activeMethod.input_type;
        const msgType = schema.message_types.find(mt => mt.name === inputType);
        return msgType?.fields || [];
    }, [activeMethod, schema]);

    const handleParamChange = (name: string, value: string) => {
        const newArgs = [...(data.args || [])];
        const idx = newArgs.findIndex(a => a.name === name);
        if (idx >= 0) {
            newArgs[idx] = { ...newArgs[idx], value };
        } else {
            newArgs.push({ name, value });
        }
        updateStatement('args', newArgs);
    };

    return (
        <div className="flex flex-col gap-2 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
                <select
                    value={data.dataProduct || ''}
                    onChange={(e) => {
                        updateStatement('dataProduct', e.target.value);
                        updateStatement('methodName', '');
                        updateStatement('args', []);
                    }}
                    className="px-2 py-1 border border-slate-200 rounded text-slate-700 outline-none text-xs bg-white w-32"
                >
                    <option value="">Select Product</option>
                    {products.map((p) => (
                        <option key={p.id} value={p.name}>
                            {p.name}
                        </option>
                    ))}
                </select>
                <span className="text-slate-400">.</span>
                <select
                    value={data.methodName || ''}
                    onChange={(e) => {
                        updateStatement('methodName', e.target.value);
                        updateStatement('args', []);
                    }}
                    className="px-2 py-1 border border-slate-200 rounded text-slate-700 outline-none text-xs bg-white w-40"
                    disabled={!data.dataProduct || loading}
                >
                    <option value="">Select Method</option>
                    {loading ? (
                        <option>Loading...</option>
                    ) : (
                        schema?.methods.map((m) => (
                            <option key={m.name} value={m.name}>
                                {m.name}
                            </option>
                        ))
                    )}
                </select>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsManual(!isManual)}
                    className="h-7 text-[10px] text-slate-500 hover:text-indigo-600 px-2"
                >
                    {isManual ? 'Use Form' : 'Manual Edit'}
                </Button>
            </div>

            {!isManual && methodParams.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-1 p-2 bg-slate-50 rounded border border-slate-100">
                    {methodParams.map((param: any) => (
                        <div key={param.name} className="flex items-center gap-2 overflow-hidden">
                            <span className="text-[10px] font-mono text-slate-500 w-20 truncate" title={param.name}>
                                {param.name}:
                            </span>
                            <input
                                type="text"
                                value={data.args?.find(a => a.name === param.name)?.value || ''}
                                onChange={(e) => handleParamChange(param.name, e.target.value)}
                                placeholder={param.type}
                                className="flex-1 px-2 py-0.5 border border-slate-200 rounded text-xs outline-none focus:border-indigo-400 font-mono"
                            />
                        </div>
                    ))}
                </div>
            )}

            {isManual && (
                <div className="mt-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Arguments (JSON-like)</span>
                    <textarea
                        value={data.args?.map(a => `${a.name}: ${a.value}`).join(', ') || ''}
                        onChange={(e) => {
                            const val = e.target.value;
                            const pairs = val.split(',').map(p => p.trim()).filter(p => p);
                            const newArgs = pairs.map(p => {
                                const [name, ...v] = p.split(':').map(x => x.trim());
                                return { name, value: v.join(':') };
                            });
                            updateStatement('args', newArgs);
                        }}
                        placeholder="arg1: val1, arg2: val2"
                        className="w-full mt-1 px-2 py-1 border border-slate-200 rounded text-xs font-mono outline-none focus:border-indigo-400 bg-white h-16 resize-none"
                    />
                </div>
            )}
        </div>
    );
};

export default function BusinessEditor({ mode, initialDsl, onDslChange, schema, meta }: BusinessEditorProps) {
    const [statements, setStatements] = useState<LogicBlockData[]>([]);
    const [preconditions, setPreconditions] = useState<LogicBlockData[]>([]);
    const [description, setDescription] = useState(meta.description || '');

    // Sync description if meta changes
    useEffect(() => {
        if (meta.description !== undefined) {
            setDescription(meta.description || '');
        }
    }, [meta.description]);

    // DnD Sensors
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event: any) => {
        const { active, over } = event;
        if (active.id !== over.id) {
            setStatements((prev) => reorderNodesInTree(prev, active.id, over.id));
        }
    };

    // Actions
    const addStatement = (parentId: string | null, type: BlockType) => {
        const newId = Math.random().toString(36).substr(2, 9);
        let newStmt: LogicBlockData;

        if (type === 'SET') {
            newStmt = { id: newId, type: 'SET', target: '', value: '' };
        } else if (type === 'TRIGGER') {
            newStmt = { id: newId, type: 'TRIGGER', actionEntity: '', actionName: '', target: '' };
        } else if (type === 'FOR') {
            newStmt = { id: newId, type: 'FOR', variable: '', entity: '', conditions: '', children: [] };
        } else if (type === 'PRECONDITION') {
            newStmt = { id: newId, type: 'PRECONDITION', label: 'check', conditions: '' };
        } else if (type === 'CALL') {
            newStmt = { id: newId, type: 'CALL', dataProduct: '', methodName: '', args: [] };
        } else {
            return;
        }

        if (type === 'PRECONDITION') {
            setPreconditions(prev => [...prev, newStmt]);
        } else {
            setStatements((prev) => addNodeToTree(prev, parentId, newStmt));
        }
    };

    const updateStatement = (id: string, field: string, value: any) => {
        if (preconditions.some(p => p.id === id)) {
            setPreconditions(prev => prev.map(p => p.id === id ? { ...p, [field]: value } : p));
        } else {
            setStatements((prev) => updateNodeInTree(prev, id, field, value));
        }
    };

    const removeStatement = (id: string) => {
        if (preconditions.some(p => p.id === id)) {
            setPreconditions(prev => prev.filter(p => p.id !== id));
        } else {
            setStatements((prev) => removeNodeFromTree(prev, id));
        }
    };

    // --- Sync from initialDsl ---
    const handleSyncFromDsl = useCallback(() => {
        if (!initialDsl) return;
        const { statements: s, preconditions: p } = parseDslToBlocks(initialDsl, mode);
        setStatements(s);
        setPreconditions(p);
    }, [initialDsl, mode]);

    // Initial sync - only on mount to prevent circular updates
    useEffect(() => {
        handleSyncFromDsl();
    }, []); // Run only once when the editor mounts (e.g., when switching tabs)

    // Logic to generate DSL from statements
    const generatedDsl = useMemo(() => {
        const renderLevel = (stmts: LogicBlockData[], level = 1): string => {
            let str = '';
            const indent = '    '.repeat(level);

            stmts.forEach((stmt) => {
                if (stmt.type === 'SET') {
                    str += `${indent}SET ${stmt.target || 'entity.prop'} = ${stmt.value || '""'};\n`;
                } else if (stmt.type === 'TRIGGER') {
                    const actionFull = stmt.actionEntity && stmt.actionName
                        ? `${stmt.actionEntity}.${stmt.actionName}`
                        : 'Action.unknown';
                    str += `${indent}TRIGGER ${actionFull} ON ${stmt.target || 'target'};\n`;
                } else if (stmt.type === 'CALL') {
                    const argsStr = stmt.args && stmt.args.length > 0
                        ? `{ ${stmt.args.map(a => `${a.name}: ${a.value || '""'}`).join(', ')} }`
                        : '{}';
                    const productName = stmt.dataProduct || 'Product';
                    const displayProduct = productName.includes(' ') ? `"${productName}"` : productName;
                    str += `${indent}CALL ${displayProduct}.${stmt.methodName || 'Method'}(${argsStr});\n`;
                } else if (stmt.type === 'FOR') {
                    str += `\n${indent}FOR (${stmt.variable || 'v'}: ${stmt.entity || 'Entity'}`;
                    if (stmt.conditions) str += ` WHERE ${stmt.conditions}`;
                    str += `) {\n`;
                    if (stmt.children && stmt.children.length > 0) {
                        str += renderLevel(stmt.children, level + 1);
                    }
                    str += `${indent}}\n`;
                }
            });
            return str;
        };

        if (mode === 'RULE') {
            let dsl = `RULE ${meta.name || 'UntitledRule'} PRIORITY ${meta.priority || 100} {\n`;
            if (meta.trigger) {
                const t = meta.trigger;
                dsl += `    ON ${t.type}(${t.entity}${t.type === 'UPDATE' && t.property ? '.' + t.property : ''})\n\n`;
            }
            dsl += renderLevel(statements);
            dsl += `}`;
            return dsl;
        } else {
            // ACTION mode
            const paramsStr = meta.parameters && meta.parameters.length > 0
                ? `(${meta.parameters.map(p => `${p.name}: ${p.type}${p.optional ? '?' : ''}`).join(', ')})`
                : '';
            let dsl = `ACTION ${meta.entityType || 'Entity'}.${meta.name || 'action'}${paramsStr} {\n`;
            if (description) {
                dsl += `    DESCRIPTION: "${description.replace(/"/g, '\\"')}"\n\n`;
            }
            preconditions.forEach(p => {
                dsl += `    PRECONDITION ${p.label || 'check'}: ${p.conditions || 'true'}\n`;
                if (p.onFailure) {
                    dsl += `        ON_FAILURE: "${p.onFailure}"\n`;
                }
            });
            dsl += `    EFFECT {\n`;
            dsl += renderLevel(statements, 2);
            dsl += `    }\n`;
            dsl += `}`;
            return dsl;
        }
    }, [statements, preconditions, mode, meta]);

    // Effect to notify parent of DSL change
    useEffect(() => {
        onDslChange(generatedDsl);
    }, [generatedDsl, onDslChange]);

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Settings className="h-4 w-4 text-indigo-500" />
                        {mode === 'RULE' ? '业务规则编辑器' : '业务动作编辑器'}
                    </h3>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleSyncFromDsl}
                        className="h-7 text-[10px] font-bold text-indigo-600 border-indigo-200 hover:bg-indigo-50"
                    >
                        <Wand2 size={12} className="mr-1" /> 从源码同步
                    </Button>
                </div>
                <div className="flex gap-2">
                    {mode === 'ACTION' && (
                        <button
                            onClick={() => addStatement(null, 'PRECONDITION')}
                            className="text-xs flex items-center gap-1 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded hover:bg-emerald-100 text-emerald-700 transition-colors font-medium"
                        >
                            <Plus size={12} /> 添加前置条件
                        </button>
                    )}
                    <button
                        onClick={() => addStatement(null, 'SET')}
                        className="text-xs flex items-center gap-1 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded hover:bg-amber-100 text-amber-700 transition-colors font-medium"
                    >
                        <Plus size={12} /> 添加赋值
                    </button>
                    <button
                        onClick={() => addStatement(null, 'TRIGGER')}
                        className="text-xs flex items-center gap-1 px-3 py-1.5 bg-purple-50 border border-purple-200 rounded hover:bg-purple-100 text-purple-700 transition-colors font-medium"
                    >
                        <Plus size={12} /> 添加动作
                    </button>
                    <button
                        onClick={() => addStatement(null, 'FOR')}
                        className="text-xs flex items-center gap-1 px-3 py-1.5 bg-indigo-50 border border-indigo-200 rounded hover:bg-indigo-100 text-indigo-700 transition-colors font-medium"
                    >
                        <Repeat size={12} /> 添加循环
                    </button>
                    <button
                        onClick={() => addStatement(null, 'CALL')}
                        className="text-xs flex items-center gap-1 px-3 py-1.5 bg-sky-50 border border-sky-200 rounded hover:bg-sky-100 text-sky-700 transition-colors font-medium"
                    >
                        <ExternalLink size={12} /> 添加调用
                    </button>
                </div>
            </div>

            <div className="bg-slate-100/50 p-4 rounded-xl border border-slate-200 min-h-[400px] space-y-4">
                {/* Preconditions Section (Action only) */}
                {mode === 'ACTION' && preconditions.length > 0 && (
                    <div className="space-y-2">
                        <div className="flex items-center gap-2 px-1">
                            <ShieldCheck size={14} className="text-emerald-500" />
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Preconditions</span>
                        </div>
                        {preconditions.map((p) => (
                            <LogicBlock
                                key={p.id}
                                id={p.id}
                                data={p}
                                updateStatement={updateStatement}
                                removeStatement={removeStatement}
                                addStatement={addStatement}
                                schema={schema}
                            />
                        ))}
                    </div>
                )}

                {/* Statements Section */}
                <div className="space-y-2">
                    {mode === 'ACTION' && (
                        <div className="flex items-center gap-2 px-1">
                            <Zap size={14} className="text-amber-500" />
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Effects</span>
                        </div>
                    )}
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                        <SortableContext items={statements.map((s) => s.id)} strategy={verticalListSortingStrategy}>
                            <div className="space-y-1">
                                {statements.map((stmt) => (
                                    <LogicBlock
                                        key={stmt.id}
                                        id={stmt.id}
                                        data={stmt}
                                        updateStatement={updateStatement}
                                        removeStatement={removeStatement}
                                        addStatement={addStatement}
                                        schema={schema}
                                    />
                                ))}
                                {statements.length === 0 && preconditions.length === 0 && (
                                    <div className="flex flex-col items-center justify-center h-[300px] border-2 border-dashed border-slate-300 rounded-lg text-slate-400 gap-3">
                                        <Box size={40} className="text-slate-200" />
                                        <p className="text-sm font-medium">从上方选择逻辑块开始构建</p>
                                    </div>
                                )}
                            </div>
                        </SortableContext>
                    </DndContext>
                </div>
            </div>

            <div className="bg-[#1e1e1e] p-4 rounded-lg shadow-inner">
                <div className="flex items-center gap-2 mb-2">
                    <Code size={14} className="text-indigo-400" />
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">实时 DSL 预览</span>
                </div>
                <pre className="font-mono text-[11px] leading-relaxed overflow-x-auto text-slate-300">
                    {generatedDsl}
                </pre>
            </div>
        </div>
    );
}
