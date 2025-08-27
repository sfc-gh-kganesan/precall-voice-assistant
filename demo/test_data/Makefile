.PHONY: clean

clean:
	rm -rf ./golden_invoices
	rm -rf ./golden_purchase_orders
	rm -rf ./m1_data
	
m1_data:
	unzip m1_data.zip

golden: golden_invoices golden_purchase_orders

golden_invoices: m1_data
	python ../scripts/manifest.py golden_invoices.manifest check
	python ../scripts/manifest.py golden_invoices.manifest materialize

golden_purchase_orders: m1_data
	python ../scripts/manifest.py golden_purchase_orders.manifest check
	python ../scripts/manifest.py golden_purchase_orders.manifest materialize
