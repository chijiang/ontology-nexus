import React, { useState, useEffect } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragOverlay
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
    Play,
    Save,
    Box,
    Zap,
    Settings,
    ArrowRight,
    Trash2,
    GripVertical,
    Plus,
    Layers,
    Code,
    FileJson,
    Activity,
    Repeat,
    CornerDownRight
} from 'lucide-react';

// --- Mock Schema Definitions ---
const SCHEMA = {
    entities: ['Supplier', 'PurchaseOrder', 'PurchaseRequisition', 'Material', 'Payment'],
    properties: {
        Supplier: ['status', 'creditLevel', 'id', 'name'],
        PurchaseOrder: ['status', 'amount', 'approvalLevel', 'orderedFrom', 'createdAt'],
        PurchaseRequisition: ['status', 'forMaterial', 'requestedBy'],
        Payment: ['status', 'amount', 'paidTo', 'executedAt'],
        Material: ['status', 'type', 'sku']
    },
    actions: {
        PurchaseOrder: ['submit', 'approve', 'reject', 'lock'],
        Payment: ['revalidate', 'execute', 'hold'],
        Notification: ['send']
    }
};

// --- Helper Functions for Tree State ---

// 递归查找并更新节点
const updateNodeInTree = (nodes, id, field, value) => {
    return nodes.map(node => {
        if (node.id === id) {
            return { ...node, [field]: value };
        }
        if (node.children) {
            return { ...node, children: updateNodeInTree(node.children, id, field, value) };
        }
        return node;
    });
};

// 递归查找并删除节点
const removeNodeFromTree = (nodes, id) => {
    return nodes
        .filter(node => node.id !== id)
        .map(node => {
            if (node.children) {
                return { ...node, children: removeNodeFromTree(node.children, id) };
            }
            return node;
        });
};

// 递归查找并添加子节点
const addNodeToTree = (nodes, parentId, newNode) => {
    if (parentId === null) {
        return [...nodes, newNode];
    }
    return nodes.map(node => {
        if (node.id === parentId) {
            return { ...node, children: [...(node.children || []), newNode] };
        }
        if (node.children) {
            return { ...node, children: addNodeToTree(node.children, parentId, newNode) };
        }
        return node;
    });
};

// 查找包含两个ID的列表并重新排序 (仅处理同一层级的排序)
const reorderNodesInTree = (nodes, activeId, overId) => {
    // 检查当前层级是否包含这两个ID
    const activeIndex = nodes.findIndex(n => n.id === activeId);
    const overIndex = nodes.findIndex(n => n.id === overId);

    if (activeIndex !== -1 && overIndex !== -1) {
        return arrayMove(nodes, activeIndex, overIndex);
    }

    // 递归检查子节点
    return nodes.map(node => {
        if (node.children) {
            return { ...node, children: reorderNodesInTree(node.children, activeId, overId) };
        }
        return node;
    });
};

// --- Components ---

const ToolItem = ({ type, label, icon: Icon, onClick, description }) => (
    <div 
    onClick= { onClick }
className = "group flex flex-col p-3 bg-white border border-slate-200 rounded-lg cursor-pointer hover:border-blue-500 hover:shadow-md transition-all mb-3"
    >
    <div className="flex items-center gap-2 mb-1" >
        <div className="p-1.5 bg-blue-50 text-blue-600 rounded-md group-hover:bg-blue-600 group-hover:text-white transition-colors" >
            <Icon size={ 16 } />
                </div>
                < span className = "font-semibold text-slate-700 text-sm" > { label } </span>
                    </div>
                    < p className = "text-xs text-slate-500 pl-9" > { description } </p>
                        </div>
);

// Recursive Logic Block
const LogicBlock = ({ id, data, updateStatement, removeStatement, addStatement }) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 50 : 'auto',
        opacity: isDragging ? 0.5 : 1,
    };

    const isLoop = data.type === 'FOR';

    return (
        <div 
      ref= { setNodeRef }
    style = { style }
    className = {`relative flex flex-col items-start gap-2 p-3 bg-white border rounded-lg shadow-sm group mb-3 transition-colors ${isLoop ? 'border-indigo-200 bg-indigo-50/30' : 'border-slate-200 hover:border-blue-400'
        }`
}
    >
    <div className="flex items-start w-full gap-3" >
        {/* Drag Handle */ }
        < div {...attributes } {...listeners } className = "mt-2 text-slate-300 cursor-grab hover:text-slate-500 flex-shrink-0" >
            <GripVertical size={ 16 } />
                </div>

{/* Content Body */ }
<div className="flex-1 w-full" >
    {/* Header Line */ }
    < div className = "flex items-center gap-2 mb-2 flex-wrap" >
        <span className={
            `text-xs font-bold px-2 py-0.5 rounded uppercase flex-shrink-0 ${data.type === 'SET' ? 'bg-amber-100 text-amber-700' :
                data.type === 'TRIGGER' ? 'bg-purple-100 text-purple-700' :
                    'bg-indigo-100 text-indigo-700'
            }`
}>
    { data.type }
    </span>

{
    data.type === 'SET' && (
        <>
        <span className="text-slate-500 text-xs font-mono" > SET </span>
            < input
    type = "text"
    value = { data.target }
    onChange = {(e) => updateStatement(id, 'target', e.target.value)
}
placeholder = "entity.prop"
className = "px-2 py-1 border border-slate-200 rounded w-32 text-slate-700 focus:border-blue-500 outline-none font-mono text-xs bg-white"
    />
    <span className="text-slate-400" >= </span>
        < input
type = "text"
value = { data.value }
onChange = {(e) => updateStatement(id, 'value', e.target.value)}
placeholder = "val"
className = "flex-1 min-w-[100px] px-2 py-1 border border-slate-200 rounded text-slate-700 focus:border-blue-500 outline-none font-mono text-xs bg-white"
    />
    </>
            )}

{
    data.type === 'TRIGGER' && (
        <>
        <span className="text-slate-500 text-xs font-mono" > TRIGGER </span>
            < select
    value = { data.actionEntity }
    onChange = {(e) => updateStatement(id, 'actionEntity', e.target.value)
}
className = "px-2 py-1 border border-slate-200 rounded text-slate-700 outline-none text-xs bg-white w-24"
    >
    <option value="" > Type </option>
{ Object.keys(SCHEMA.actions).map(t => <option key={ t } value = { t } > { t } </option>) }
</select>
    < span className = "text-slate-400" >.</span>
        < select
value = { data.actionName }
onChange = {(e) => updateStatement(id, 'actionName', e.target.value)}
className = "px-2 py-1 border border-slate-200 rounded text-slate-700 outline-none text-xs bg-white w-24"
    >
    { SCHEMA.actions[data.actionEntity]?.map(a => <option key={ a } value = { a } > { a } < /option>) || <option>...</option >}
    </select>
    < span className = "text-slate-500 text-xs font-mono" > ON </span>
        < input
type = "text"
value = { data.target }
onChange = {(e) => updateStatement(id, 'target', e.target.value)}
placeholder = "var"
className = "w-20 px-2 py-1 border border-slate-200 rounded text-slate-700 focus:border-blue-500 outline-none font-mono text-xs bg-white"
    />
    </>
            )}

{
    data.type === 'FOR' && (
        <>
        <div className="flex items-center bg-white border border-indigo-200 rounded px-2 py-1 shadow-sm" >
            <input 
                    className="w-6 text-center text-xs font-bold text-indigo-700 outline-none border-b border-indigo-100 focus:border-indigo-500 bg-transparent"
    value = { data.variable }
    onChange = {(e) => updateStatement(id, 'variable', e.target.value)
}
placeholder = "v"
    />
    <span className="mx-1 text-slate-400 text-xs" >: </span>
        < select
value = { data.entity }
onChange = {(e) => updateStatement(id, 'entity', e.target.value)}
className = "text-xs font-semibold text-indigo-700 outline-none bg-transparent"
    >
    { SCHEMA.entities.map(e => <option key={ e } value = { e } > { e } </option>) }
    </select>
    </div>
    < span className = "text-xs font-medium text-slate-500" > WHERE </span>
        < input
className = "flex-1 min-w-[150px] bg-white border border-slate-200 rounded px-2 py-1 text-xs font-mono text-slate-600 outline-none focus:border-indigo-500"
value = { data.conditions }
onChange = {(e) => updateStatement(id, 'conditions', e.target.value)}
placeholder = "e.g. v.amount > 100"
    />
    </>
            )}
</div>

{/* Recursive Children Container */ }
{
    isLoop && (
        <div className="pl-4 border-l-2 border-indigo-200 ml-1 mt-2" >
            <div className="flex flex-col gap-2 min-h-[40px] pt-2 pb-1" >
                <SortableContext 
                  items={ data.children || [] }
    strategy = { verticalListSortingStrategy }
        >
    {
        data.children?.map((child, idx) => (
            <LogicBlock 
                      key= { child.id }
                      id = { child.id }
                      data = { child }
                      updateStatement = { updateStatement }
                      removeStatement = { removeStatement }
                      addStatement = { addStatement }
            />
                  ))
    }
        </SortableContext>

    {
        (!data.children || data.children.length === 0) && (
            <div className="text-[10px] text-slate-400 italic py-2" >
                Empty loop.Add logic below.
                  </div>
                )
    }
    </div>

    {/* Nested Add Buttons */ }
    <div className="flex gap-2 mt-2 pt-2 border-t border-indigo-100 border-dashed" >
        <button onClick={ () => addStatement(id, 'SET') } className = "text-[10px] flex items-center gap-1 px-2 py-1 bg-white border border-slate-200 rounded hover:border-indigo-500 text-slate-600 transition-colors" >
            <CornerDownRight size={ 10 } /> Set
                </button>
                < button onClick = {() => addStatement(id, 'TRIGGER')
} className = "text-[10px] flex items-center gap-1 px-2 py-1 bg-white border border-slate-200 rounded hover:border-indigo-500 text-slate-600 transition-colors" >
    <CornerDownRight size={ 10 } /> Trigger
        </button>
        < button onClick = {() => addStatement(id, 'FOR')} className = "text-[10px] flex items-center gap-1 px-2 py-1 bg-white border border-slate-200 rounded hover:border-indigo-500 text-slate-600 transition-colors" >
            <CornerDownRight size={ 10 } /> Nested Loop
                </button>
                </div>
                </div>
          )}
</div>

{/* Delete Button */ }
<button 
          onClick={ () => removeStatement(id) }
className = "p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors flex-shrink-0"
    >
    <Trash2 size={ 14 } />
        </button>
        </div>
        </div>
  );
};

export default function KGBuilder() {
    // State for the Rule Header
    const [ruleName, setRuleName] = useState("ComplexRiskAudit");
    const [priority, setPriority] = useState(90);

    const [trigger, setTrigger] = useState({
        event: "UPDATE",
        entity: "Supplier",
        property: "creditLevel"
    });

    const [rootScope, setRootScope] = useState({
        variable: "s",
        entity: "Supplier",
        conditions: 's.creditLevel == "C"'
    });

    // Recursive State Structure
    const [statements, setStatements] = useState([
        { id: '1', type: 'SET', target: 's.auditRequired', value: 'true' },
        {
            id: '2',
            type: 'FOR',
            variable: 'po',
            entity: 'PurchaseOrder',
            conditions: 'po.status == "Open"',
            children: [
                { id: '2a', type: 'SET', target: 'po.status', value: '"RiskHold"' },
                { id: '2b', type: 'TRIGGER', actionEntity: 'Notification', actionName: 'send', target: 'po' }
            ]
        }
    ]);

    const [dslCode, setDslCode] = useState("");

    // Recursive Transpiler Logic
    useEffect(() => {
        const renderStatements = (stmts, level = 2) => {
            let str = "";
            const indent = "    ".repeat(level);

            stmts.forEach(stmt => {
                if (stmt.type === 'SET') {
                    str += `${indent}SET ${stmt.target} = ${stmt.value};\n`;
                } else if (stmt.type === 'TRIGGER') {
                    const actionFull = stmt.actionEntity && stmt.actionName
                        ? `${stmt.actionEntity}.${stmt.actionName}`
                        : 'Action.unknown';
                    str += `${indent}TRIGGER ${actionFull} ON ${stmt.target};\n`;
                } else if (stmt.type === 'FOR') {
                    str += `\n${indent}FOR (${stmt.variable}: ${stmt.entity}`;
                    if (stmt.conditions) str += ` WHERE ${stmt.conditions}`;
                    str += `) {\n`;
                    // Recursion
                    if (stmt.children && stmt.children.length > 0) {
                        str += renderStatements(stmt.children, level + 1);
                    }
                    str += `${indent}}\n`;
                }
            });
            return str;
        };

        const generateDSL = () => {
            let code = `RULE ${ruleName} PRIORITY ${priority} {\n`;

            // Trigger
            code += `    ON ${trigger.event}(${trigger.entity}`;
            if (trigger.event === 'UPDATE' && trigger.property) {
                code += `.${trigger.property}`;
            }
            code += `)\n\n`;

            // Root Scope
            code += `    FOR (${rootScope.variable}: ${rootScope.entity}`;
            if (rootScope.conditions) {
                code += ` WHERE ${rootScope.conditions}`;
            }
            code += `) {\n`;

            // Render Tree
            code += renderStatements(statements);

            code += `    }\n`;
            code += `}`;
            setDslCode(code);
        };

        generateDSL();
    }, [ruleName, priority, trigger, rootScope, statements]);

    // DnD Sensors
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event) => {
        const { active, over } = event;
        if (active.id !== over.id) {
            // Use recursive reorder helper
            setStatements((prev) => reorderNodesInTree(prev, active.id, over.id));
        }
    };

    // Actions
    const addStatement = (parentId, type) => {
        const newId = Math.random().toString(36).substr(2, 9);
        let newStmt;

        if (type === 'SET') {
            newStmt = { id: newId, type: 'SET', target: 'entity.prop', value: 'val' };
        } else if (type === 'TRIGGER') {
            newStmt = { id: newId, type: 'TRIGGER', actionEntity: 'Notification', actionName: 'send', target: 'var' };
        } else if (type === 'FOR') {
            newStmt = { id: newId, type: 'FOR', variable: 'x', entity: 'Entity', conditions: '', children: [] };
        }

        setStatements(prev => addNodeToTree(prev, parentId, newStmt));
    };

    const updateStatement = (id, field, value) => {
        setStatements(prev => updateNodeInTree(prev, id, field, value));
    };

    const removeStatement = (id) => {
        setStatements(prev => removeNodeFromTree(prev, id));
    };

    return (
        <div className= "flex flex-col h-screen bg-slate-50 text-slate-800 font-sans overflow-hidden" >

        {/* Header */ }
        < header className = "h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 shadow-sm z-10 flex-shrink-0" >
            <div className="flex items-center gap-2" >
                <div className="w-8 h-8 bg-blue-600 rounded-md flex items-center justify-center text-white" >
                    <Activity size={ 20 } />
                        </div>
                        < h1 className = "font-bold text-lg text-slate-800" > KG Rule Builder < span className = "text-xs font-normal text-slate-400 ml-1" > v2.1 Nested < /span></h1 >
                            </div>
                            < div className = "flex items-center gap-3" >
                                <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-md transition-colors" >
                                    <FileJson size={ 16 } /> Load
                                        </button>
                                        < button className = "flex items-center gap-2 px-4 py-1.5 text-sm font-medium bg-slate-900 text-white rounded-md hover:bg-slate-800 transition-colors shadow-sm" >
                                            <Save size={ 16 } /> Save Rule
                                                </button>
                                                </div>
                                                </header>

                                                < main className = "flex-1 flex overflow-hidden" >

                                                    {/* LEFT: Toolbox */ }
                                                    < div className = "w-64 bg-slate-50 border-r border-slate-200 flex flex-col flex-shrink-0" >
                                                        <div className="p-4" >
                                                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4" > Toolbox </h2>

                                                                < div className = "mb-6" >
                                                                    <h3 className="text-xs font-semibold text-slate-600 mb-2 px-1" > Logic Blocks </h3>
                                                                        < ToolItem
    type = "SET"
    label = "Set Property"
    icon = { Box }
    description = "Update a property value"
    onClick = {() => addStatement(null, 'SET')
}
              />
    < ToolItem
type = "TRIGGER"
label = "Trigger Action"
icon = { Zap }
description = "Invoke an entity action"
onClick = {() => addStatement(null, 'TRIGGER')}
              />
    < ToolItem
type = "FOR"
label = "Nested Loop"
icon = { Repeat }
description = "Iterate over related entities"
onClick = {() => addStatement(null, 'FOR')}
              />
    </div>
    </div>

    < div className = "mt-auto p-4 border-t border-slate-200" >
        <div className="text-xs text-slate-400 text-center" >
            Tip: Use "Nested Loop" to create complex graph traversals.
             </div>
                </div>
                </div>

{/* CENTER: Canvas */ }
<div className="flex-1 bg-slate-100 p-8 overflow-y-auto flex flex-col items-center" >

    {/* Rule Container */ }
    < div className = "w-full max-w-3xl bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden flex flex-col flex-shrink-0 mb-12" >

        {/* 1. Rule Header */ }
        < div className = "p-5 border-b border-slate-100 bg-slate-50/50" >
            <div className="flex items-center gap-4" >
                <div className="flex-1" >
                    <label className="block text-xs font-bold text-slate-400 uppercase mb-1" > Rule Name </label>
                        < input
type = "text"
value = { ruleName }
onChange = {(e) => setRuleName(e.target.value)}
className = "w-full text-lg font-bold text-slate-800 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 outline-none transition-colors"
    />
    </div>
    < div className = "w-24" >
        <label className="block text-xs font-bold text-slate-400 uppercase mb-1" > Priority </label>
            < input
type = "number"
value = { priority }
onChange = {(e) => setPriority(Number(e.target.value))}
className = "w-full text-sm font-mono text-slate-600 bg-white border border-slate-200 rounded px-2 py-1 outline-none focus:border-blue-500"
    />
    </div>
    </div>
    </div>

{/* 2. Trigger Section */ }
<div className="p-5 border-b border-slate-100 relative" >
    <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500" > </div>
        < div className = "flex items-center gap-2 mb-3" >
            <Zap size={ 16 } className = "text-amber-500" />
                <span className="text-sm font-bold text-slate-700" > Trigger </span>
                    </div>

                    < div className = "flex items-center gap-3 bg-amber-50/50 p-3 rounded-lg border border-amber-100" >
                        <span className="text-sm font-medium text-slate-500" > ON </span>
                            < select
value = { trigger.event }
onChange = {(e) => setTrigger({ ...trigger, event: e.target.value })}
className = "bg-white border border-amber-200 text-slate-700 text-sm rounded px-2 py-1 outline-none"
    >
    <option value="UPDATE" > UPDATE </option>
        < option value = "CREATE" > CREATE </option>
            < option value = "DELETE" > DELETE </option>
                </select>
                < span className = "text-slate-400" > (</span>
                    < select 
                    value = { trigger.entity }
onChange = {(e) => setTrigger({ ...trigger, entity: e.target.value })}
className = "bg-white border border-amber-200 text-slate-700 text-sm rounded px-2 py-1 outline-none"
    >
    { SCHEMA.entities.map(e => <option key={ e } value = { e } > { e } </option>) }
    </select>

{
    trigger.event === 'UPDATE' && (
        <>
        <span className="text-slate-400" >.</span>
            < select
    value = { trigger.property }
    onChange = {(e) => setTrigger({ ...trigger, property: e.target.value })
}
className = "bg-white border border-amber-200 text-slate-700 text-sm rounded px-2 py-1 outline-none"
    >
    { SCHEMA.properties[trigger.entity]?.map(p => <option key={ p } value = { p } > { p } </option>) }
    </select>
    </>
                  )}
<span className="text-slate-400" >)</span>
    </div>

    < div className = "absolute left-8 -bottom-5 w-0.5 h-5 bg-slate-200 z-0" > </div>
        </div>

{/* 3. Scope Section */ }
<div className="p-5 bg-slate-50/30 flex-1 relative" >
    <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500" > </div>

        < div className = "flex items-center gap-2 mb-3" >
            <Settings size={ 16 } className = "text-blue-500" />
                <span className="text-sm font-bold text-slate-700" > Root Scope </span>
                    </div>

                    < div className = "mb-4 flex flex-wrap items-center gap-3 p-3 bg-white border border-slate-200 rounded-lg shadow-sm z-10 relative" >
                        <span className="text-sm font-medium text-slate-500" > FOR </span>
                            < div className = "flex items-center bg-slate-100 rounded px-2 py-1" >
                                <input 
                      className="w-8 bg-transparent text-center text-sm font-mono outline-none border-b border-slate-300 focus:border-blue-500"
value = { rootScope.variable }
onChange = {(e) => setRootScope({ ...rootScope, variable: e.target.value })}
                    />
    < span className = "mx-1 text-slate-400" >: </span>
        < select
value = { rootScope.entity }
onChange = {(e) => setRootScope({ ...rootScope, entity: e.target.value })}
className = "bg-transparent text-sm font-semibold text-blue-700 outline-none"
    >
    { SCHEMA.entities.map(e => <option key={ e } value = { e } > { e } </option>) }
    </select>
    </div>
    < span className = "text-sm font-medium text-slate-500" > WHERE </span>
        < input
className = "flex-1 bg-slate-50 border border-slate-200 rounded px-2 py-1 text-sm font-mono text-slate-600 outline-none focus:border-blue-500"
value = { rootScope.conditions }
onChange = {(e) => setRootScope({ ...rootScope, conditions: e.target.value })}
                  />
    </div>

{/* Recursive Statements Zone */ }
<div className="pl-6 border-l-2 border-dashed border-slate-200 ml-4 pb-4" >
    <div className="mb-2 flex items-center gap-2" >
        <ArrowRight size={ 14 } className = "text-slate-300" />
            <span className="text-xs font-bold text-slate-400 uppercase" > Logic Chain </span>
                </div>

                < DndContext
sensors = { sensors }
collisionDetection = { closestCenter }
onDragEnd = { handleDragEnd }
    >
    <SortableContext 
                      items={ statements }
strategy = { verticalListSortingStrategy }
    >
    <div className="space-y-2 min-h-[100px]" >
    {
        statements.map((stmt, index) => (
            <LogicBlock 
                            key= { stmt.id } 
                            id = { stmt.id }
                            data = { stmt } 
                            updateStatement = { updateStatement }
                            removeStatement = { removeStatement }
                            addStatement = { addStatement }
            />
                        ))
    }
        </div>
        </SortableContext>
        </DndContext>

{/* Root Add Buttons */ }
<div className="mt-4 flex gap-2" >
    <button onClick={ () => addStatement(null, 'SET') } className = "text-xs flex items-center gap-1 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 text-blue-700 transition-colors font-medium" >
        <Plus size={ 12 } /> Add Set
            </button>
            < button onClick = {() => addStatement(null, 'TRIGGER')} className = "text-xs flex items-center gap-1 px-3 py-1.5 bg-purple-50 border border-purple-200 rounded hover:bg-purple-100 text-purple-700 transition-colors font-medium" >
                <Plus size={ 12 } /> Add Trigger
                    </button>
                    < button onClick = {() => addStatement(null, 'FOR')} className = "text-xs flex items-center gap-1 px-3 py-1.5 bg-indigo-50 border border-indigo-200 rounded hover:bg-indigo-100 text-indigo-700 transition-colors font-medium" >
                        <Repeat size={ 12 } /> Add Loop
                            </button>
                            </div>
                            </div>
                            </div>

                            </div>
                            </div>

{/* RIGHT: Live Code Preview */ }
<div className="w-96 bg-[#1e1e1e] flex flex-col border-l border-slate-800 shadow-xl flex-shrink-0" >
    <div className="h-10 bg-[#252526] flex items-center justify-between px-4 border-b border-[#333]" >
        <span className="text-xs font-bold text-slate-400 flex items-center gap-2" >
            <Code size={ 14 } /> GENERATED DSL
                </span>
                < span className = "flex h-2 w-2 rounded-full bg-green-500" > </span>
                    </div>
                    < div className = "flex-1 overflow-auto p-4 custom-scrollbar" >
                        <pre className="font-mono text-xs leading-relaxed" style = {{ color: '#d4d4d4' }}>
                        {
                            dslCode.split('\n').map((line, i) => {
                                let color = '#d4d4d4';
                                if (line.includes('RULE') || line.includes('PRIORITY')) color = '#c586c0';
                                else if (line.includes('ON') || line.includes('FOR')) color = '#569cd6';
                                else if (line.includes('SET') || line.includes('TRIGGER')) color = '#4fc1ff';

                                return (
                                    <div key= { i } style = {{ color }
                            }>
                            { line }
                            </div>
                            );
                        })}
</pre>
    </div>
    </div>
    </main>
    </div>
  );
}