#!/bin/bash

# Prompt user for input
snow connection list
read -p "Which SNOW CLI connection do you want to use? " snow_connection

# Paths to the files
makefile="./Makefile"

# Copy files
cp $makefile.template $makefile

# Replace placeholders in Makefile file using | as delimiter
sed -i "" "s|<<snow_connection>>|$snow_connection|g" $makefile

echo "$makefile is ready to use."
