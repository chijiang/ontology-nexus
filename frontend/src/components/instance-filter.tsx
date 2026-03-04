// frontend/src/components/instance-filter.tsx
'use client'

import { useState, useEffect } from 'react'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Plus, X, Filter } from 'lucide-react'
import { useTranslations } from 'next-intl'

interface SchemaNode {
    name: string
    label?: string
    dataProperties?: string[]
}

interface FilterCondition {
    key: string
    value: string
}

export interface SearchParams {
    className: string
    keyword: string
    filters: FilterCondition[]
}

interface InstanceFilterProps {
    onSearch: (params: SearchParams) => void
    loading?: boolean
}

export function InstanceFilter({ onSearch, loading }: InstanceFilterProps) {
    const t = useTranslations('components.filter')
    const token = useAuthStore((state) => state.token)
    const [classes, setClasses] = useState<SchemaNode[]>([])
    const [selectedClass, setSelectedClass] = useState<string>('')
    const [keyword, setKeyword] = useState('')
    const [filters, setFilters] = useState<FilterCondition[]>([])
    const [loadingClasses, setLoadingClasses] = useState(true)

    useEffect(() => {
        if (token) {
            loadClasses()
        }
    }, [token])

    const loadClasses = async () => {
        try {
            setLoadingClasses(true)
            const res = await graphApi.getSchema()
            setClasses(res.data.nodes || [])
        } catch (err) {
            console.error('Failed to load classes:', err)
        } finally {
            setLoadingClasses(false)
        }
    }

    const handleAddFilter = () => {
        setFilters([...filters, { key: '', value: '' }])
    }

    const handleRemoveFilter = (index: number) => {
        setFilters(filters.filter((_, i) => i !== index))
    }

    const handleFilterChange = (index: number, field: 'key' | 'value', value: string) => {
        const newFilters = [...filters]
        newFilters[index][field] = value
        setFilters(newFilters)
    }

    const handleSearch = () => {
        if (!selectedClass) return
        onSearch({
            className: selectedClass,
            keyword,
            filters: filters.filter(f => f.key && f.value)
        })
    }

    const selectedClassData = classes.find(c => c.name === selectedClass)

    return (
        <div className="bg-white rounded-lg border px-4 py-3 shadow-sm">
            <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2 text-primary font-bold mr-2">
                    <Filter className="h-4 w-4" />
                    <span className="text-xs uppercase tracking-wider">{t('filter')}</span>
                </div>

                {/* 类型选择 */}
                <div className="flex items-center gap-2">
                    <select
                        value={selectedClass}
                        onChange={(e) => setSelectedClass(e.target.value)}
                        className="min-w-[140px] px-3 py-1.5 border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary/30 bg-slate-50/50"
                        disabled={loadingClasses}
                    >
                        <option value="">{t('selectType')}</option>
                        {[...classes]
                            .sort((a, b) => a.name.localeCompare(b.name))
                            .map((cls) => (
                                <option key={cls.name} value={cls.name}>
                                    {cls.name}
                                </option>
                            ))}
                    </select>
                </div>

                <div className="flex-1 min-w-[200px] relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                        placeholder={t('searchPlaceholder')}
                        value={keyword}
                        onChange={(e) => setKeyword(e.target.value)}
                        className="w-full pl-9 h-9 text-sm bg-slate-50/50 border-slate-200"
                    />
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleAddFilter}
                        disabled={!selectedClass}
                        className="h-9 px-3 text-xs font-medium border-dashed border-slate-300 hover:border-primary hover:text-primary transition-colors"
                    >
                        <Plus className="h-3.5 w-3.5 mr-1" />
                        {t('addCondition')}
                    </Button>
                    <Button
                        onClick={handleSearch}
                        disabled={!selectedClass || loading}
                        className="h-9 px-6 bg-primary hover:opacity-90 text-white shadow-sm font-medium"
                    >
                        {loading ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                        ) : (
                            <>
                                <Search className="h-4 w-4 mr-2" />
                                {t('searchButton')}
                            </>
                        )}
                    </Button>
                </div>
            </div>

            {/* 属性过滤条件 */}
            {filters.length > 0 && (
                <div className="pt-3 mt-3 border-t border-slate-100 space-y-2">
                    {filters.map((filter, index) => (
                        <div key={index} className="flex items-center gap-3 animate-in fade-in slide-in-from-top-1 duration-200">
                            <select
                                value={filter.key}
                                onChange={(e) => handleFilterChange(index, 'key', e.target.value)}
                                className="w-[180px] px-3 py-1.5 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary/30"
                            >
                                <option value="">{t('selectProperty')}</option>
                                {selectedClassData?.dataProperties?.map((prop) => (
                                    <option key={prop} value={prop}>
                                        {prop}
                                    </option>
                                ))}
                            </select>
                            <span className="text-slate-400 font-medium">=</span>
                            <Input
                                placeholder={t('propertyValue')}
                                value={filter.value}
                                onChange={(e) => handleFilterChange(index, 'value', e.target.value)}
                                className="flex-1 max-w-[300px] h-9 text-sm border-slate-200"
                            />
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRemoveFilter(index)}
                                className="h-9 w-9 p-0 text-slate-400 hover:text-red-500 hover:bg-red-50"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
