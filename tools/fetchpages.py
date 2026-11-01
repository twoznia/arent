import sys, os, re, hashlib, urllib.request, concurrent.futures as cf
OUT=sys.argv[1]; urls=[u.strip() for u in open(sys.argv[2]) if u.strip()]
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/124"}
seen=set(); 
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60) as r:
            return u, r.geturl(), r.read().decode('utf-8','replace')
    except Exception as e:
        return u, None, str(e)
todo=list(dict.fromkeys(urls)); res={}
while todo:
    batch=[u for u in todo if u not in seen]; todo=[]
    seen.update(batch)
    with cf.ThreadPoolExecutor(8) as ex:
        for u,final,body in ex.map(get,batch):
            if final is None: print("FAIL",u,body); continue
            res[u]=final
            fn=os.path.join(OUT,hashlib.md5(u.encode()).hexdigest()+'.html')
            open(fn,'w').write(u+'\n'+final+'\n'+body)
            for m in re.findall(r'href="(https://arent\.pl/[^"?#]*/page/\d+/)"',body):
                if m not in seen: todo.append(m)
print(len(res), "pages")
