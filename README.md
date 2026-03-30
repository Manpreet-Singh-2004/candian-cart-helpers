# Install the Environment using the command

conda env create -f environment.yml

# Activate the environment using the command

## Mac/Linux

python3 -m venv venv
source venv/bin/activate

## Windows

python -m venv venv
venv\Scripts\activate

## Using mini conda

conda activate cart_env

# pip install python-dotenv pymongo

pip freeze > requirements.txt
