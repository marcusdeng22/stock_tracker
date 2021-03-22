//first drop the original database (inside mongo client):
//use procurement
//db.dropDatabase()
//then run this (outside mongo client):
//mongo scripts/debug_users.js

conn = new Mongo();
db = conn.getDB("stock");
db["stocks"].drop();
db["md-stocks"].drop();

print("resetting db to debug data");

db["md-stocks"].insert({"ticker": "BSJO", "own": true, "star": false, "indb": true, "notes": ""})
db["md-stocks"].insert({"ticker": "NMZ", "own": true, "star": false, "indb": true, "notes": ""})
db["md-stocks"].insert({"ticker": "WKHS", "own": true, "star": true, "indb": true, "notes": ""})

print("done")