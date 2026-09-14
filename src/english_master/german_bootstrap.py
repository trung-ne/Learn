"""Original-authored German bootstrap knowledge graph (12.5B)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import validate_instance
from english_master.language_profiles import knowledge_graph_id

TIERS = ("A1.1","A1.2","A2.1","A2.2","B1.1","B1.2","B2.1","B2.2","C1.1","C1.2","C2.1","C2.2")
DIMENSIONS = ("grammar","vocabulary_senses","functions","pronunciation","discourse","pragmatics","collocations","lexical_chunks","topics","skills")
TARGETS = {
 "grammar": ("sein und haben im Präsens","bestimmte und unbestimmte Artikel","Akkusativ bei häufigen Verben","Modalverben im Alltag","Perfekt mit haben und sein","Präteritum häufiger Verben","Nebensätze mit weil und dass","trennbare Verben in Hauptsätzen","Konjunktiv II für höfliche Bitten","Passiv und unpersönliche Formen","Nominalisierung und komplexe Ergänzungen","Register, Modus und Satzklammer präzise steuern"),
 "vocabulary_senses": ("Begrüßung und persönliche Angaben","Familie, Personen und Orte","Essen, Einkaufen und Mengen","Arbeit, Freizeit und Termine","Reisen, Gesundheit und Erfahrungen","Medien, Beziehungen und Ereignisse","Gesellschaft, Umwelt und Entscheidungen","Bildung, Beruf und öffentliche Dienste","abstrakte Bewertung und Argumentation","wissenschaftliche und institutionelle Begriffe","fachsprachliche Bedeutungsunterscheidungen","präzise Wortwahl über Register hinweg"),
 "functions": ("begrüßen und sich verabschieden","sich vorstellen und Informationen erfragen","etwas bestellen und bezahlen","Pläne vereinbaren und Hilfe anbieten","über Erlebnisse berichten","Meinungen begründen und nachfragen","Optionen aushandeln und Probleme lösen","eine Position erklären und einschränken","formell diskutieren und zusammenfassen","Vorschläge bewerten und widersprechen","implizite Absichten erschließen","adressatengerecht argumentieren"),
 "pronunciation": ("Alphabet, Vokallänge und Wortakzent","Umlaute und ch-Laute unterscheiden","Satzakzent in kurzen Aussagen","Endungen und Konsonantenfolgen","Intonation in Erzählungen","Reduktion in flüssiger Alltagssprache","Rhythmus in längeren Äußerungen","Klangmuster in formellen Gesprächen","Prosodie für Haltung und Fokus","regionale Varianten einordnen","präzise Laut-Buchstaben-Zuordnung","ausdrucksvolle Prosodie kontrollieren"),
 "discourse": ("kurze Aussagen mit und und aber verbinden","eine Person oder einen Ort ordnen","ein Ereignis zeitlich erzählen","Pläne und Gründe strukturieren","Absätze mit Verweisen verbinden","ein Thema über mehrere Beiträge entwickeln","Behauptung und Begründung verknüpfen","mehrteilige Argumente signalisieren","Quellen und Sichtweisen zusammenführen","lange Erklärungen gliedern","rhetorische Rahmung und Schlussfolgerung","genresensible Diskursarchitektur"),
 "pragmatics": ("Begrüßung, Anrede und Distanz","direkte Bitten höflich formulieren","Dank, Entschuldigung und Reparatur","Einladungen sozial passend machen","Zustimmung und Widerspruch taktvoll äußern","Register in unbekannten Situationen wählen","Rat abschwächen und Gesicht wahren","Macht, Nähe und Indirektheit beachten","institutionelle Höflichkeit steuern","Ironie und Andeutung erkennen","kulturelle Absichten vorsichtig deuten","Identität und Publikum strategisch ausrichten"),
 "collocations": ("heißen, wohnen und kommen aus","haben, machen und gehen im Alltag","eine Bestellung aufgeben und bezahlen","einen Termin vereinbaren und vorbereiten","eine Reise machen und Erfahrung sammeln","eine Beziehung pflegen und Ereignis erleben","eine Entscheidung treffen und Problem lösen","eine Rolle spielen und Verantwortung übernehmen","eine Schlussfolgerung ziehen und These stützen","eine Untersuchung durchführen und Ergebnis bewerten","eine feine Unterscheidung treffen","Bedeutung und Register präzise kombinieren"),
 "lexical_chunks": ("Guten Morgen und Auf Wiedersehen","Ich heiße ... und Woher kommen Sie?","Ich hätte gern ... und Was kostet das?","Könnten Sie ...? und Wann passt es?","Meiner Erfahrung nach ...","Ich bin der Meinung, dass ...","Einerseits ... andererseits ...","Es spricht einiges dafür, dass ...","Es ist hervorzuheben, dass ...","Allerdings ist zu beachten, dass ...","Nicht X, sondern Y ...","Zusammenfassend lässt sich sagen ..."),
 "topics": ("Begrüßung und persönliche Welt","Familie, Zuhause und Umgebung","Essen, Einkaufen und Tagesablauf","Arbeit, Freizeit und Termine","Reisen, Gesundheit und Erfahrungen","Medien, Beziehungen und Veranstaltungen","Umwelt, Technik und Entscheidungen","Bildung, Beruf und Gesellschaft","Institutionen, Forschung und globale Fragen","Kultur, Ethik und Werte","Spezialwissen und Unsicherheit","komplexe Systeme und Weltbilder"),
 "skills": ("kurze deutsche Alltagskontakte verstehen und führen","vorhersehbare Transaktionen bewältigen","ein einfaches Ereignis erzählen","einen Plan auf Deutsch koordinieren","eine Meinung zusammenhängend erklären","an einem vertrauten Gespräch teilnehmen","Informationen bewerten und reagieren","eine begründete Interaktion aufrechterhalten","Quellen in eine formelle Aufgabe integrieren","Genauigkeit in anspruchsvollen Aufgaben steuern","nuancierte Fachkommunikation interpretieren","anspruchsvolle Kommunikation gestalten und kritisieren"),
}

def build_population() -> dict[str, Any]:
    nodes=[]
    for ti,tier in enumerate(TIERS):
        for dimension in DIMENSIONS:
            node_id=knowledge_graph_id("de",tier,dimension)
            prerequisites=[]; edges=[]
            if ti:
                prior=knowledge_graph_id("de",TIERS[ti-1],dimension); prerequisites=[prior]; edges=[{"source":prior,"target":node_id,"relation":"PREREQUISITE"}]
            name=TARGETS[dimension][ti]
            nodes.append({"schema_version":"1.0","record_type":"multilingual_knowledge_graph_node","language_code":"de","id":node_id,"tier":tier,"dimension":dimension,"name":name,"description":f"Original project-authored German planning target for {tier}: {name}.","prerequisites":prerequisites,"dependency_edges":edges,"status":"DRAFT","authorship":"PROJECT_AUTHORED"})
    value={"schema_version":"1.0","record_type":"multilingual_knowledge_graph_population","population_id":"PENDING","language_code":"de","nodes":nodes,"tiers":list(TIERS),"dimensions":list(DIMENSIONS),"content_status":"UNREVIEWED","fixture_only":True,"external_content_used":False}
    value["population_id"]="kgpop_"+sha256_json({k:v for k,v in value.items() if k!="population_id"})
    validate_population(value)
    return value

def validate_population(value: dict[str,Any]) -> dict[str,Any]:
    validate_instance(value,"multilingual-knowledge-graph-population-v1")
    by_id={node["id"]:node for node in value["nodes"]}
    expected={knowledge_graph_id("de",tier,dimension) for tier in TIERS for dimension in DIMENSIONS}
    if len(value["nodes"])!=120 or set(by_id)!=expected: raise ValueError("German bootstrap must contain the complete 120-node language-qualified matrix")
    for node in value["nodes"]:
        if node["language_code"]!="de" or any(not ref.startswith("kg_de_") for ref in node["prerequisites"]): raise ValueError(f"cross-language German graph reference: {node['id']}")
        if {edge["source"] for edge in node["dependency_edges"]}!=set(node["prerequisites"]): raise ValueError(f"dependency mismatch: {node['id']}")
    return value

def write_population(output: Path) -> Path:
    if output.exists(): raise FileExistsError(f"refusing to overwrite immutable population: {output}")
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(build_population(),ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8"); return output
