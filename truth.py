#!/usr/bin/env python3.3
import cgitb
import cgi
import itertools
from math import ceil
from qm import qm
import colors
import json
import re
from fractions import Fraction
import os
from srcdot import source_to_graph

#seval = lambda x: compile(ast.literal_eval(x))
seval = lambda x: eval(x,{'__builtins__': {}})

def gray(x):
	"""gray code"""
	return (x >> 1) ^ x

def binstr_to_booltuple(binstr):
	return tuple([c == '1' for c in binstr])
	#return tuple(map(lambda c: c == '1', binstr))

def get_bool_table(g,lennames):
	posses = list(itertools.product([False,True],repeat=lennames))
	combi = list(zip(posses, (itertools.starmap(g,posses))))
	ma = dict(combi)
	return (combi, ma)

def numavg(listofnumbers):
	return Fraction(sum(listofnumbers),len(listofnumbers))

def avg(tuples):
	#print(colors.ofri(tuples))
	if len(tuples) == 0: raise Exception("cant average empty set")
	if len(tuples) == 1: return tuples[0]
	res = [numavg(x) for x in zip(*tuples)]
	assert len(res) == 3
	#print(colors.ofri(res))
	return res

bts = lambda x: "1" if x else "0"
	
def ascii_table(names, combi):
	yield "<pre>"
	
	
	# ascii table
	for i in names: yield i + "\t"
	yield "F"
	
	
	j = 0
	for i in combi:
		for k in i[0]: yield bts(k) + "\t\n"
		yield bts(i[1])
		j+=1
		if j==1:
			yield "\n"
			j=0
	
	yield "</pre>"

def do_table(names, g, combi, ma, groups=[]):
	#ascii_table(names, combi)

	nparam = len(names)
	
	yield "<table border=1>\n"
	yield "<tr>\n"
	yield "<th>\n"
	axis1 = ceil(Fraction(nparam , 2))
	axis2 = nparam - axis1
	yield "<table style='white-space: nowrap'><tr><th>&nbsp;<tr><th style='width:2em'><th><th>{}<tr><th style='text-align:center' colspan=3>{}</table>".format("".join(names[:axis1]), "".join(names[axis1:]))
	
	for i in range(pow(2,axis1)):
		yield "<th>" + bin(gray(i))[2:].zfill(axis1) + "\n"
	
	yield "</tr>\n"
	
	for i in range(pow(2,axis2)):
		yield "<tr>\n<th>" + bin(gray(i))[2:].zfill(axis2) + "</th>\n"
		for j in range(pow(2,axis1)):
			binstr = bin((gray(j) << axis2) | gray(i))[2:].zfill(nparam)
			bt = binstr_to_booltuple(binstr)
			cs = 			[color			for (fun,color,funtext,idx) in groups if fun(*bt)]
			classes = " ".join(	["part{}".format(idx)	for (fun,color,funtext,idx) in groups if fun(*bt)])
			if len(cs) > 0:
				yield "<td class='{}' style='".format(classes)
				yield "background-color: rgb({},{},{});".format(*htmlrange(colors.genrgb(avg(cs))))
				yield "'>"
			else:
				yield "<td>"

			yield "{}".format(ma[binstr_to_booltuple(binstr)])
			yield "</td>\n"
	
	yield "</tr>\n"
	yield "</table>\n"

htmlrange = lambda color: [int(x*255) for x in color]

def tuple_to_int(x):
	su = 0
	for i in range(len(x)):
		su += pow(2,i) if x[len(x)-i-1] else 0
	return su

def gencp(names=None, lang="python"):
	pythonmap = lambda x: x
	verilogdic = {
		"and": "&",
		"not": "~",
	}
	verilogmap = lambda x: verilogdic[x]
	use = pythonmap if lang == "python" else verilogmap
	def constructproduct(x):
		j = -1
		buf = []
		for char in x:
			j += 1
			if char == "X":
				continue
			if char == "0":
				buf.append(use("not"))
			if names is None:
				buf.append("x[" + str(j) + "]")
			else:
				buf.append(names[j])
			buf.append(use("and"))
		if len(buf) == 0: return "True"
		if buf[-1] == use("and"): del buf[-1]
		return "(" + " ".join(buf) + ")"
	return constructproduct

def mapcode(x,cb):
	orgx = x
	x = re.sub(" xor "," ^ ",x)
	x = re.sub("([A-z]+) nor ([A-z]+)","not (\\1 or \\2)",x)
	x = re.sub("([A-z]+) nand ([A-z]+)","not (\\1 and \\2)",x)
	x = re.sub("\+"," or ",x)
	x = re.sub("\|"," or ",x)
	x = re.sub("!", " not ",x)
	x = re.sub("-", " not ",x)
	x = re.sub("\\\\"," not ",x)
	x = re.sub("\*"," and ",x)
	x = re.sub("&"," and ",x)
	if orgx != x:
		cb("warning, changed fun!")
	return x

def cleancode(x,cb):
	orgx = x
	x = re.sub("[^0-9A-z _\^|&()]","",x)
	if orgx != x:
		cb("removed illegal chars!")
	return x

cleannames = lambda x: re.sub("[\W\d]", "", x)

def servepage(formtarget, form):
	yield "<!doctype html><head><script src='//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js'></script><script>"
	yield """
	function app(partid,kmapclass,bol) {
		var selector = kmapclass + " " + ".part" + partid;
		$(selector).css('font-weight',(bol ? 'bold' : 'normal'));
	}
	function hov(partid, kmapclass) {
		return app(partid,kmapclass,true);
	}
	function unhov(partid, kmapclass) {
		return app(partid,kmapclass,false);
	}
	"""
	yield "</script><style>.warning { color: red } .minterm:hover { background-color: yellow; } td, th { padding: 5px; }</style><title>Karnaugh Map</title></head><body>"
	
	formnames = form["names"].value if "names" in form else "a,b,c,d"
	formfunstr = form["funstr"].value if "funstr" in form else "a and (not b and not d or b and c and not d)"
	checked1 = form["type"].value == "small" if "type" in form else True
	checked2 = not checked1

	yield """
<form action="{}" method="post">
<p><input name="names" size="40" value="{}" id="names"></p>
<table>
<tr>
<td>
<input name="type" value="small" {} type="radio">
<td>
<p><input name="funstr" size="40" value="{}"></p>
<tr>
<td>
<input onclick="document.getElementById('names').value='a,b,c,d,e,f,g,h,i,j'" name="type" value="big" {} type="radio">
<td>
<textarea name="userdata" cols=30 rows=10>1011011111
1111100111
1101111111
1011011011
1010001010
1000111011
0011111011</textarea>
</table>
<p><input type="submit"></p>
</form>
	""".format(formtarget, formnames, "checked" if checked1 else "", formfunstr, "checked" if checked2 else "")
	if "funstr" not in form or "names" not in form:
		yield "missing funstr={} names={}".format("funstr" in form, "names" in form)
		return
	
	#names = ["a","b","c","d"]
	d = form["names"].value.split(",")
	names = [cleannames(x) for x in d]
	for i in names:
		if len(i) == 0:
			raise Exception("invalid!")
	
	counter = itertools.count()

	if form["type"].value == "small":
		warningmsg = []
		def cb(m):
			warningmsg.append(m)
		funbody = cleancode(mapcode(form["funstr"].value,cb),cb).strip()
		funtext = "lambda {}: {}".format(",".join(names), funbody)
		if len(warningmsg) > 0:
			print("<div class='warning'>{}</div>".format(" ".join(warningmsg)))
		yield "input: <pre>{}</pre>".format(funtext)
		make_inline_svg(funbody)
		g = seval(funtext)
		yield from karnaugh(names, g, counter)
	#def g(a,b,c,d): return a and (not b and not d or b and c and not d)
	else:

		genfuntriple = lambda y, x: (y, x, seval(x))
		inst1 = gencp(lang="verilog")
		inst2 = gencp()
		funs = [genfuntriple(inst1(x), "lambda *x: " + inst2(x)) for x in [x.strip() for x in form["userdata"].value.strip().split("\n")]]

		"""[
			"1011011111", # a
			"1111100111", # b
			"1101111111", # c
			"1011011011", # d
			"1010001010", # e
			"1000111011", # f
			"0011111011", # g
		]]"""

		for (verilogtext, funtext, fun) in funs:
			yield from karnaugh(names, fun, counter)


remove_xml_header = lambda x: re.sub("<\?xml.*\?>", "", x)
remove_doctype = lambda x: re.sub("<!DOCTYPE [^>]+>", "", x, re.MULTILINE | re.IGNORECASE | re.DOTALL)
make_inline_svg = lambda funbody: remove_doctype(
	remove_xml_header(
		source_to_graph(funbody)
			.create(format="svg")
			.decode("utf-8")
	)
)

def karnaugh(names, g, counter):
	(combi, ma) = get_bool_table(g,len(names))
	#do_table(names, g, combi, ma)
	
	myid = next(counter)
	myclassname = "karnaugh{}".format(myid)
	myjsonid = json.dumps("." + myclassname)
	yield "<div class='{}'>\n".format(myclassname)

	j = 0
	l = []
	for k in sorted(ma.keys(), key=tuple_to_int):
		v = ma[k]
		if v: l.append(j)
		j += 1
	
	#print("calling qm: <pre>ones = {}</pre>".format(json.dumps(l)))
	res = [x.zfill(len(names)) for x in qm(ones=l)]
	#print("result: <pre>{}</pre>".format(json.dumps(res)))
	
	parts = list(map(gencp(names), res))
	gencode = lambda ps: "lambda " + ", ".join(names) + ": " + ps
	def genhtmlcode(ps):
		li = list(zip(ps,itertools.count()))
		middle = ["<span class='minterm' onmouseover='hov({0},{2})' onmouseout='unhov({0},{2})'>{1}</span>".format(j,i,myjsonid) for (i,j) in li]
		return "lambda " + ", ".join(names) + ": " + " or ".join(middle)

	funbody = " or ".join(parts)
	code = gencode(funbody)
	htmlcode = genhtmlcode(parts)

	yield "output:\n<pre>"
	yield htmlcode
	yield "</pre>\n"
	fun = seval(code)
	pair = get_bool_table(fun, len(names))

	funtexts = [gencode(x) for x in parts]
	funs = [seval(x) for x in funtexts]
	yield from do_table(names,fun,*pair,groups=list(zip(funs,colors.gethsvs(),funtexts,itertools.count())))
	
	# schematic
	yield make_inline_svg(funbody)

	# check equivalence
	res = pair[1]
	for i in ma.keys():
		if not i in res.keys():
			assert False
		if res[i] != ma[i]:
			yield "key", i
			yield "expected", ma[i]
			yield "got", res[i]
			assert False

	#assert res == ma
	yield "</div>"

if __name__ == "__main__":
	cgitb.enable()
	form = cgi.FieldStorage()
	print("Content-Type: text/html\n")
	myprint = lambda x: print(x,end="")
	#def myprint(x):
	#	if not isinstance(x, str):
	#		raise Exception(x)
	#	print(x, end="")
	list(map(myprint, servepage(os.path.basename(__file__), form)))
