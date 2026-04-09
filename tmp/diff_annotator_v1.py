import json

def annotate_v1(d1, d2):
    out = {}
    for k, v in d1.items():
        if k not in d2:
            out["#### REMOVED_" + k] = annotate_all(v)
        else:
            v2 = d2[k]
            if isinstance(v, dict) and isinstance(v2, dict):
                out[k] = annotate_v1(v, v2)
            elif isinstance(v, list) and isinstance(v2, list):
                out[k] = diff_list_v1(v, v2)
            elif v != v2:
                out["#### CHANGED_" + k] = "#### " + str(v)
            else:
                out[k] = v
    return out

def diff_list_v1(l1, l2):
    out = []
    for i, v in enumerate(l1):
        if i >= len(l2):
            out.append(annotate_all(v))
        else:
            v2 = l2[i]
            if isinstance(v, dict) and isinstance(v2, dict):
                out.append(annotate_v1(v, v2))
            elif isinstance(v, list) and isinstance(v2, list):
                out.append(diff_list_v1(v, v2))
            elif v != v2:
                if isinstance(v, str):
                    out.append("#### " + v)
                else:
                    out.append("#### CHANGED: " + str(v))
            else:
                out.append(v)
    return out

def annotate_all(v):
    if isinstance(v, dict):
        return {"#### " + str(k): annotate_all(val) for k, val in v.items()}
    elif isinstance(v, list):
        return [annotate_all(item) for item in v]
    else:
        return "#### " + str(v)

with open(r"c:\Users\nikhi\Desktop\DESK\Projects\New folder\APISEC\backend\fixtures\schema_diff_showcase\diff_showcase_v1.openapi.json", "r") as f1:
    v1 = json.load(f1)
with open(r"c:\Users\nikhi\Desktop\DESK\Projects\New folder\APISEC\backend\fixtures\schema_diff_showcase\diff_showcase_v2.openapi.json", "r") as f2:
    v2 = json.load(f2)

annotated_v1 = annotate_v1(v1, v2)

with open(r"c:\Users\nikhi\Desktop\DESK\Projects\New folder\APISEC\reports\v1.json", "w") as f:
    json.dump(annotated_v1, f, indent=2)

print("Annotated v1 created!")
