text = ""

with open("bootstrap_3.4.1_replacement.css", "r") as f:
	for l in f:
		text += l.strip()

textDict = {}
top = True
braceCount = 0
key = ""
val = ""
for c in text:
	if c != "{" and braceCount == 0:
		key += c
	else:
		val += c
		if c == "{":
			braceCount += 1
		if c == "}":
			braceCount -= 1
			if braceCount == 0:
				textDict[key] = val
				key = ""
				val = ""
print(len(textDict))

# exactTerms = ["@font-face", ".glyphicon"]
# searchTerms = ["glyphicon-refresh", "glyphicon-chevron-up", "glyphicon-chevron-down", "button", "btn", "input", "input-group", "input-group-addon", "input-sm", "form-control"]

# exactTerms = ["@font-face"]	#can't use font-family in .glyphicon for some reason
# searchTerms = ["button", "btn", "input", "input-group", "input-group-addon", "input-sm", "form-control"]

excludedTerms = ["@font-face", "glyphicon", "tab"]

with open("bootstrap_3.4.1_replacement2.css", "w") as f:
	for k in textDict:
		# for e in exactTerms:
		# 	if e == k.strip():
		# 		f.write(k + " " + textDict[k] + "\n\n")
		# for s in searchTerms:
		# 	if s in k.lower():
		# 		f.write(k + " " + textDict[k] + "\n\n")
		matched = False
		for ex in excludedTerms:
			if ex in k.lower():
				matched = True
				break
		if not matched:
			# f.write(k + " " + textDict[k] + "\n\n")
			f.write(k + textDict[k])