"""Regenerate the DEC-082 availability mask under the HERALD_64 section 6 canonical names."""
import csv,collections,json,hashlib,sys
OLD="data/processed/france_ze2020/fr_ze2020_relation_availability_mask.csv"
EST=sys.argv[1]
OUT="data/processed/france_ze2020/fr_ze2020_relation_availability_mask_v2.csv"
RENAME={"commuting_strict_ex_ante":"flow","ze_similarity":"similarity",
        "intra_ze_sector":"__drop_node_attr__","cross_ze_same_sector":"__drop_node_attr__",
        "temporal_precedence_signal":"__superseded__","sector_to_sector_comovement":"__superseded__"}
old=list(csv.DictReader(open(OLD)))
est=list(csv.DictReader(open(EST)))
years=sorted({int(x["decision_year"]) for x in old})
# admitted families and their per-year edge counts, from DEC-096
adm={"precedence_intra","precedence_cross"}
cnt=collections.Counter()
for x in est:
    if x["relation_family"] in adm and x["bh_rejected"]=="True":
        cnt[(x["relation_family"],int(x["decision_year"]))]+=1
est_years={int(x["decision_year"]) for x in est}
rows=[]
# flow: carry the old commuting rows over under the canonical name
for x in old:
    if x["relation_family"]=="commuting_strict_ex_ante":
        y=dict(x); y["relation_family"]="flow"; rows.append(y)
# similarity / specialization: node attributes, recorded as not-an-edge
for fam,src in [("similarity","ze_similarity"),("specialization",None)]:
    for yr in years:
        base=next((x for x in old if x["relation_family"]==src and int(x["decision_year"])==yr), None) if src else None
        rows.append({"relation_family":fam,"decision_year":yr,
            "availability_status":"node_attribute_not_an_edge",
            "unavailable_reason":"reclassified_by_HERALD_64_section_3.1",
            "source_snapshot_year":(base or {}).get("source_snapshot_year",""),
            "source_release_date":(base or {}).get("source_release_date",""),
            "snapshot_age_years":(base or {}).get("snapshot_age_years",""),
            "expected_edge_count":"","actual_edge_count":"",
            "provenance":"resemblance asserts no interaction; retained as a node attribute (HERALD_64 3.1)"})
# precedence families
for fam in ["precedence_intra","precedence_cross"]:
    for yr in years:
        if yr in est_years:
            n=cnt[(fam,yr)]
            rows.append({"relation_family":fam,"decision_year":yr,
                "availability_status":"derived_available","unavailable_reason":"",
                "source_snapshot_year":yr,"source_release_date":"","snapshot_age_years":0,
                "expected_edge_count":81,"actual_edge_count":n,
                "provenance":"estimate_fr_ze2020_relations.py, BH q=0.10, placebo-surviving (DEC-096)"})
        else:
            rows.append({"relation_family":fam,"decision_year":yr,
                "availability_status":"unavailable","unavailable_reason":"insufficient_history",
                "source_snapshot_year":"","source_release_date":"","snapshot_age_years":"",
                "expected_edge_count":81,"actual_edge_count":0,
                "provenance":"outside the estimated window; needs t-1, t and t+1 growth (HERALD_64 section 4)"})
# comovement: excluded
for yr in years:
    rows.append({"relation_family":"comovement","decision_year":yr,
        "availability_status":"unavailable","unavailable_reason":"failed_placebo_gate",
        "source_snapshot_year":"","source_release_date":"","snapshot_age_years":"",
        "expected_edge_count":81,"actual_edge_count":0,
        "provenance":"window-fragile: R1 5/7 on 2019-2025, 4/7 on 2018-2024; excluded by DEC-096 10.1"})
flds=list(old[0].keys())
w=csv.DictWriter(open(OUT,"w",newline=""),fieldnames=flds); w.writeheader()
for r in rows: w.writerow({k:r.get(k,"") for k in flds})
c=collections.Counter((r["relation_family"],r["availability_status"]) for r in rows)
print("linhas:",len(rows))
for k,v in sorted(c.items()): print(" ",k,v)
canon={"flow","precedence_intra","precedence_cross","comovement","similarity","specialization"}
assert {r["relation_family"] for r in rows}==canon, "nomes fora do canónico"
print("\nnomes canónicos: OK (HERALD_64 secção 6)")
