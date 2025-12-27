.PHONY: clean

all: dist zip

clean:
	rm -rf ./dist

dist:
	npm install
	npm run build

zip:
	cd dist && rm -f workflow.zip && zip -r -X ./workflow.zip .

run:
	curl -X POST http://localhost:3000/run -F "file=@dist/workflow.zip"
