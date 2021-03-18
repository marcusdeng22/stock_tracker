#!/usr/bin/env python3

import pymongo as pm
from getpass import getpass
import hashlib
import os

client = pm.MongoClient()["stock"]
db = client["users"]

print("Connected to MongoDB")

while True:
	uname = input("Enter user name: ")

	if db.find_one({"username": uname}) != None:
		print("User already exists; try again")
	else:
		break

while True:
	pw = getpass("Enter password: ")
	verify = getpass("Re-enter password: ")

	if pw != verify:
		print("Passwords don't match; try again")
	else:
		break

# have username and password; hash the password and generate a salt
salt = os.urandom(32)
hash = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100000)

# write to db
db.insert_one({
	"username": uname,
	"hash": hash,
	"salt": salt
})

print("User added!")