'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { NoConfigurationAlert } from '@/components/common/NoConfigurationAlert'
import { useAppStore } from '@/stores/appStore'
import { ProductFilters } from '@/components/products/ProductFilters'
import { ProductGrid } from '@/components/products/ProductGrid'
import { ProductDetailView } from '@/components/products/ProductDetailView'
import { BenchmarkingSection } from '@/components/products/BenchmarkingSection'
import { ProductComparison } from '@/components/products/ProductComparison'
import { FilterBar } from '@/components/common/FilterBar'
import { AppHeader } from '@/components/common/AppHeader'

function ProductsContent() {
  const searchParams = useSearchParams()
  const { activeConfigId, isInitializing } = useAppStore()

  // Filter state
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedSubcategories, setSelectedSubcategories] = useState<string[]>([])
  const [selectedProducts, setSelectedProducts] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch products to derive category from subcategory
  const { filters } = useAppStore()
  const { data: allProducts } = useQuery({
    queryKey: ['product-metrics', filters],
    queryFn: () => dashboardApi.getProductMetrics(filters),
    enabled: !!activeConfigId,
  })

  // Read subcategory from URL params and derive parent category
  useEffect(() => {
    const subcategoryParam = searchParams.get('subcategory')
    if (subcategoryParam && allProducts) {
      // Find the parent category by looking at products with this subcategory
      const productWithSubcategory = allProducts.find(
        p => p.productSubcategory === subcategoryParam
      )

      if (productWithSubcategory) {
        setSelectedCategories([productWithSubcategory.productCategory])
        setSelectedSubcategories([subcategoryParam])
      }
    }
  }, [searchParams, allProducts])

  // Handler for selecting a single product (detail view)
  const handleProductSelect = (productId: string) => {
    setSelectedProducts([productId])
  }

  // Handler for toggling products (multi-select for comparison)
  const handleProductToggle = (productId: string) => {
    setSelectedProducts((prev) =>
      prev.includes(productId)
        ? prev.filter((id) => id !== productId)
        : [...prev, productId]
    )
  }

  // Handler for closing detail view
  const handleCloseDetail = () => {
    setSelectedProducts([])
  }

  // Handler to toggle filters visibility
  const [showFilters, setShowFilters] = useState(true)
  const isDetailView = selectedProducts.length === 1

  // Auto-hide filters when entering detail view
  useEffect(() => {
    if (isDetailView) {
      setShowFilters(false)
    } else {
      setShowFilters(true)
    }
  }, [isDetailView])

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <AppHeader title="Product Analytics" />

      <main className="container mx-auto px-4 py-8">
        {isInitializing ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : !activeConfigId ? (
          <NoConfigurationAlert />
        ) : (
          <>
            {/* Filter Bar */}
            <FilterBar className="mb-6" />

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Filters Sidebar - Hide on detail view */}
              {(!isDetailView || showFilters) && (
                <div className="lg:col-span-1">
                  <ProductFilters
                    selectedCategories={selectedCategories}
                    selectedSubcategories={selectedSubcategories}
                    selectedProducts={selectedProducts}
                    searchQuery={searchQuery}
                    onCategoriesChange={setSelectedCategories}
                    onSubcategoriesChange={setSelectedSubcategories}
                    onProductsChange={setSelectedProducts}
                    onSearchQueryChange={setSearchQuery}
                  />
                </div>
              )}

              {/* Main Content - Full width on detail view when filters hidden */}
              <div className={`space-y-6 ${isDetailView && !showFilters ? 'lg:col-span-4' : 'lg:col-span-3'}`}>
                {/* Show Filters Button - Only visible on detail view when filters are hidden */}
                {isDetailView && !showFilters && (
                  <button
                    onClick={() => setShowFilters(true)}
                    className="mb-4 px-4 py-2 bg-card border border-border rounded-lg text-sm font-medium text-foreground hover:bg-accent/20 transition-colors"
                  >
                    Show Filters
                  </button>
                )}

                {/* Product Discovery or Detail View */}
                {selectedProducts.length === 1 ? (
                  <ProductDetailView
                    productId={selectedProducts[0]}
                    onClose={handleCloseDetail}
                  />
                ) : (
                  <ProductGrid
                    selectedCategories={selectedCategories}
                    selectedSubcategories={selectedSubcategories}
                    selectedProducts={selectedProducts}
                    searchQuery={searchQuery}
                    onProductToggle={handleProductToggle}
                    onProductSelect={handleProductSelect}
                  />
                )}

                {/* Product Comparison (when 2+ products selected) */}
                {selectedProducts.length >= 2 && (
                  <ProductComparison selectedProductIds={selectedProducts} />
                )}

                {/* Benchmarking Section (Collapsed by default) */}
                <BenchmarkingSection
                  selectedCategory={selectedCategories[0]}
                  selectedSubcategory={selectedSubcategories[0]}
                  selectedProductId={selectedProducts[0]}
                />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default function ProductsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    }>
      <ProductsContent />
    </Suspense>
  )
}
