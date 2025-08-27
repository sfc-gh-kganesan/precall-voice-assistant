# Initialize test data

**Step 1**: Copy and download m1_data.zip from Google Drive to this directory
<https://drive.google.com/file/d/1ni5qLSs04Tk_fJgMKZxeLFnpEUvr3Bb3/view?usp=drive_link>

**Step 2**: Run: `make golden_invoices`

This command will:

    - Extract the contents of `m1_data.zip` (if not done already)
    - Run an integrity check on each file listed in `golden_invoices.manifest`
    - Copy each file listed in the manifest to `golden_invoices`

**Step 3**: Run `make golden_purchase_orders`

    - Extract the contents of `m1_data.zip` (if not done already)
    - Run an integrity check on each file listed in `golden_purchase_orders.manifest`
    - Copy each file listed in the manifest to `golden_purchase_orders`

__Note: you can run `make golden` to do both steps at once__

# Creating and updating manifests

To create a new manifest, perhaps for a new eval data set, simply create a new .manifest 
text file. Each line in this file should be a relative reference to a file contained in
`m1_data`.

Then, run the python helper script: `python ../scripts/manifest.py <manifest file> write`.
This command will add the file hashes to the file.

