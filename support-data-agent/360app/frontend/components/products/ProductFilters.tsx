'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi, productsApi } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { ProductSearchResult } from '@/types'
import { Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ProductFiltersProps {
  selectedCategories: string[]
  selectedSubcategories: string[]
  selectedProducts: string[]
  searchQuery: string
  onCategoriesChange: (categories: string[]) => void
  onSubcategoriesChange: (subcategories: string[]) => void
  onProductsChange: (products: string[]) => void
  onSearchQueryChange: (query: string) => void
}

export function ProductFilters({
  selectedCategories,
  selectedSubcategories,
  selectedProducts,
  searchQuery,
  onCategoriesChange,
  onSubcategoriesChange,
  onProductsChange,
  onSearchQueryChange,
}: ProductFiltersProps) {
  const { filters, activeConfigId } = useAppStore()
  const [searchInput, setSearchInput] = useState(searchQuery)
  const [debouncedSearch, setDebouncedSearch] = useState(searchQuery)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput)
      onSearchQueryChange(searchInput)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput, onSearchQueryChange])

  // Fetch categories
  const { data: categories } = useQuery({
    queryKey: ['category-metrics', filters],
    queryFn: () => dashboardApi.getCategoryMetrics(filters),
    enabled: !!activeConfigId,
  })

  // Fetch subcategories for selected category
  const { data: subcategories } = useQuery({
    queryKey: ['subcategory-metrics', selectedCategories[0], filters],
    queryFn: () => dashboardApi.getSubcategoryMetrics(selectedCategories[0]!, filters),
    enabled: !!activeConfigId && selectedCategories.length === 1,
  })

  // Search products
  const { data: searchResults } = useQuery({
    queryKey: ['product-search', debouncedSearch, selectedCategories[0], selectedSubcategories[0]],
    queryFn: () => productsApi.searchProducts(
      debouncedSearch,
      selectedCategories[0],
      selectedSubcategories[0]
    ),
    enabled: !!activeConfigId && debouncedSearch.length >= 2,
  })

  const toggleCategory = (categoryName: string) => {
    if (selectedCategories.includes(categoryName)) {
      onCategoriesChange(selectedCategories.filter(c => c !== categoryName))
      onSubcategoriesChange([]) // Clear subcategories when category is deselected
    } else {
      onCategoriesChange([categoryName]) // Single selection for now
      onSubcategoriesChange([]) // Clear subcategories when changing category
    }
  }

  const toggleSubcategory = (subcategoryName: string) => {
    if (selectedSubcategories.includes(subcategoryName)) {
      onSubcategoriesChange(selectedSubcategories.filter(s => s !== subcategoryName))
    } else {
      onSubcategoriesChange([subcategoryName]) // Single selection for now
    }
  }

  const toggleProduct = (productId: string) => {
    if (selectedProducts.includes(productId)) {
      onProductsChange(selectedProducts.filter(p => p !== productId))
    } else {
      onProductsChange([...selectedProducts, productId])
    }
  }

  const clearAllFilters = () => {
    onCategoriesChange([])
    onSubcategoriesChange([])
    onProductsChange([])
    setSearchInput('')
  }

  const hasActiveFilters = selectedCategories.length > 0 ||
                          selectedSubcategories.length > 0 ||
                          selectedProducts.length > 0 ||
                          searchQuery.length > 0

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-foreground">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearAllFilters}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            Clear all
          </button>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search products..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      {/* Search Results */}
      {searchResults && searchResults.length > 0 && (
        <div className="border border-border rounded-md bg-background max-h-48 overflow-y-auto">
          <div className="text-xs font-medium text-muted-foreground px-3 py-2 border-b border-border">
            Search Results ({searchResults.length})
          </div>
          {searchResults.map((product: ProductSearchResult) => (
            <button
              key={product.productId}
              onClick={() => toggleProduct(product.productId)}
              className={cn(
                'w-full text-left px-3 py-2 hover:bg-accent transition-colors border-b border-border last:border-b-0',
                selectedProducts.includes(product.productId) && 'bg-accent'
              )}
            >
              <div className="text-sm font-medium text-foreground">{product.productName}</div>
              <div className="text-xs text-muted-foreground">{product.productCategory}</div>
            </button>
          ))}
        </div>
      )}

      {/* Category Filter */}
      <div>
        <div className="text-sm font-medium text-foreground mb-2">Category</div>
        <div className="space-y-1">
          {categories?.map((category) => (
            <button
              key={category.categoryName}
              onClick={() => toggleCategory(category.categoryName)}
              className={cn(
                'w-full text-left px-3 py-2 rounded-md text-sm transition-colors',
                selectedCategories.includes(category.categoryName)
                  ? 'bg-primary text-primary-foreground font-medium'
                  : 'bg-background border border-border hover:bg-accent text-foreground'
              )}
            >
              {category.categoryName}
              <span className="ml-2 text-xs opacity-70">({category.totalCases})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Subcategory Filter */}
      {selectedCategories.length === 1 && subcategories && subcategories.length > 0 && (
        <div>
          <div className="text-sm font-medium text-foreground mb-2">Subcategory</div>
          <div className="space-y-1">
            {subcategories.map((subcat) => (
              <button
                key={subcat.subcategoryName}
                onClick={() => toggleSubcategory(subcat.subcategoryName)}
                className={cn(
                  'w-full text-left px-3 py-2 rounded-md text-sm transition-colors',
                  selectedSubcategories.includes(subcat.subcategoryName)
                    ? 'bg-primary text-primary-foreground font-medium'
                    : 'bg-background border border-border hover:bg-accent text-foreground'
                )}
              >
                {subcat.subcategoryName}
                <span className="ml-2 text-xs opacity-70">({subcat.totalCases})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Selected Products */}
      {selectedProducts.length > 0 && (
        <div>
          <div className="text-sm font-medium text-foreground mb-2">
            Selected Products ({selectedProducts.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedProducts.map((productId) => (
              <button
                key={productId}
                onClick={() => toggleProduct(productId)}
                className="flex items-center gap-1 px-2 py-1 bg-primary text-primary-foreground text-xs rounded-md hover:bg-primary/80 transition-colors"
              >
                <span className="truncate max-w-[150px]">{productId}</span>
                <X className="w-3 h-3" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
