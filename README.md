# Install the Environment using the command

Advised to use conda

```bash
conda env create -f environment.yml
```

# Activate the environment using the command

## Mac/Linux

python3 -m venv venv
source venv/bin/activate

## Windows

python -m venv venv
venv\Scripts\activate

## Using mini conda

```bash
conda activate cart_env
```

# pip install python-dotenv pymongo

pip freeze > requirements.txt

# Download MongoDump from this link

https://fastdl.mongodb.org/tools/db/mongodb-database-tools-windows-x86_64-100.15.0.zip

and set them to system environment path. then run the program

# How to run?

Activate the environment

```bash
conda activate cart_env
```

and then run

```bash
 python menu.py
```

# Management

## Backups

Sunfarm backups will be done within the `/Sunfarm/Backups/` folder and based on what DB dev or prod

## Product

When working on products for eg **Sunfarm** work on `/Sunfarm/Products/WorkingOnCurrently` they must only contain the files like json or csv or so on, No Code. All the Coding files have to be created in code folder `/Sunfarm/Products/WorkingOnCurrently`.

original folder contains the base original product csv we recieved and in short the biggest list of products.

Finalized contains the final csv or json to be inserted

temp has temp files which maybe a mix of things
