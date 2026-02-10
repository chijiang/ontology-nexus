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
            const res = await graphApi.getSchema(token!)
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
        <div className="bg-white rounded-lg border p-4 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <Filter className="h-4 w-4" />
                {t('filter')}
            </div>

            {/* 类型选择 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">{t('entityType')}</label>
                    <select
                        value={selectedClass}
                        onChange={(e) => setSelectedClass(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        disabled={loadingClasses}
                    >
                        <option value="">{t('selectType')}</option>
                        {classes.map((cls) => (
                            <option key={cls.name} value={cls.name}>
                                {cls.name}
                            </option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">{t('keywordSearch')}</label>
                    <Input
                        placeholder={t('searchPlaceholder')}
                        value={keyword}
                        onChange={(e) => setKeyword(e.target.value)}
                        className="w-full"
                    />
                </div>

                <div className="flex items-end">
                    <Button
                        onClick={handleSearch}
                        disabled={!selectedClass || loading}
                        className="w-full"
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
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-gray-600">{t('propertyFilter')}</label>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleAddFilter}
                        disabled={!selectedClass}
                    >
                        <Plus className="h-3 w-3 mr-1" />
                        {t('addCondition')}
                    </Button>
                </div>

                {filters.map((filter, index) => (
                    <div key={index} className="flex items-center gap-2">
                        <select
                            value={filter.key}
                            onChange={(e) => handleFilterChange(index, 'key', e.target.value)}
                            className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">{t('selectProperty')}</option>
                            {selectedClassData?.dataProperties?.map((prop) => (
                                <option key={prop} value={prop}>
                                    {prop}
                                </option>
                            ))}
                        </select>
                        <span className="text-gray-400">=</span>
                        <Input
                            placeholder={t('propertyValue')}
                            value={filter.value}
                            onChange={(e) => handleFilterChange(index, 'value', e.target.value)}
                            className="flex-1"
                        />
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveFilter(index)}
                            className="p-2"
                        >
                            <X className="h-4 w-4 text-gray-400" />
                        </Button>
                    </div>
                ))}
            </div>
        </div>
    )
}
