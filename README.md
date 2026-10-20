# AI FACTORY — ausführbarer MVP

Next.js/React-Oberfläche, FastAPI, SQLModel mit PostgreSQL oder SQLite, echte OpenAI-kompatible Chat-Completions-Anbindung. Es gibt keine Demo-Projekte und keine simulierten Produktantworten.

## Lokal starten

Voraussetzungen: Python 3.12+, Node 22+, optional Docker. Zwei Terminals:

```bash
cp .env.example .env
# .env bearbeiten: FACTORY_TOKEN und MODEL_API_KEY setzen
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
set -a
. ./.env
set +a
cd backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

```bash
cd frontend
npm ci
npm run dev
```

http://localhost:3000 öffnen. FACTORY_TOKEN in das Zugangsfeld eingeben. Projekt beschreiben, Modellkosten für diesen Auftrag freigeben, erstellen. Schlüssel bleiben serverseitig; der Oberflächenzugangsschlüssel bleibt im Arbeitsspeicher des Browsers. Ein Neuladen erfordert erneute Eingabe.

Alternativ: `cp .env.example .env`, sichere Werte und Modellzugang setzen, dann `docker compose up --build`. PostgreSQL wird persistent gestartet. Frontend: http://localhost:3000. Sonderzeichen im PostgreSQL-Passwort müssen für die DATABASE_URL URL-kompatibel sein. Für Cloud-Builds hinter Unternehmensproxys die jeweilige CA als BuildKit-Secret mounten und pip/npm mit dieser CA konfigurieren; TLS-Prüfung nicht abschalten.

## Tatsächlicher Ablauf

1. Orchestrator nimmt freigegebene Aufträge an, maximal vier gleichzeitig in der Warteschlange und eine Generierung zur Zeit.
2. Architect, Model Engineer und Designer führen getrennte echte Modellaufrufe aus und reichen Ergebnisse weiter.
3. Developer erzeugt vollständige Textdateien als strukturiertes JSON. Pfad-, Größen- und Anzahlgrenzen werden serverseitig geprüft.
4. Unveränderliche Revision wird auf Festplatte gespeichert. Python wird mit AST, JSON mit JSON-Parser geprüft; README muss vorhanden sein.
5. Bei Fehlern bekommt Debugger die Dateien und den Bericht, maximal zwei Korrekturen. Jede Version bleibt erhalten.
6. Optimizer liefert eine dokumentierte Prüfung. Empfehlungen verändern Code nicht ungeprüft.
7. UI zeigt persistierte Ereignisse per Polling. ZIP enthält die aktuelle Revision. `syntax_passed` bedeutet ausschließlich erfolgreiche statische Prüfung.

Das System trainiert kein neues Basismodell: Es entwickelt Anwendungen, die vorhandene Modelle integrieren. Modellqualität, Kontextfenster und Ausgabelimit begrenzen Projektgröße und Zuverlässigkeit. Unterbrochene Jobs werden beim Neustart als `interrupted` markiert; kein stilles Wiederholen kostenpflichtiger Aufrufe.

## Optionaler Container-Test

Nur auf einem dedizierten lokalen Entwicklungsrechner: `docker pull python:3.12-slim`, dann `ENABLE_SANDBOX=true` im Backend setzen und neu starten. Docker-CLI und lokaler Daemon müssen vom Backend erreichbar sein; Projektverzeichnisse müssen für den Daemon dieselben absoluten Pfade haben. Die Standard-Compose-Konfiguration mountet bewusst keinen Docker-Socket und deaktiviert diese Funktion.

Im Projekt auf „Container-Test“ klicken und Ausführung bestätigen. Es läuft ausschließlich der feste Befehl `python -B -m unittest discover -s tests -v`: kein Netzwerk, keine Fähigkeiten, read-only-Dateisystem, unprivilegierter Benutzer, RAM-/CPU-/Prozesslimit und 45 Sekunden Zeitlimit. Das Image wird nicht automatisch heruntergeladen, keine generierten Installationsbefehle laufen auf dem Host. Keine Tests bedeutet keinen Erfolg. Drittanbieterabhängigkeiten sind in diesem Image nicht verfügbar. Generierte Tests können unvollständig sein; auch ein erfolgreicher Lauf ist kein umfassender Qualitäts- oder Sicherheitsnachweis. Container sind keine perfekte Grenze gegen feindlichen Code; für Mehrbenutzerbetrieb separate VM-/MicroVM-Runner verwenden.

## Konfiguration und Kosten

- `MODEL_API_KEY`: Schlüssel zum Modellanbieter; niemals in Projektdateien oder im Frontend hinterlegen.
- `MODEL_BASE_URL`: vertrauenswürdiger OpenAI-kompatibler Endpunkt (Chat Completions mit JSON-Ausgabe).
- `MODEL_NAME`: Modell; Standard `gpt-4.1-mini`.
- `MAX_MODEL_CALLS`: Aufruflimit je Auftrag, Standard 12. Jede Antwort ist auf 12.000 Ausgabetokens begrenzt.
- `FACTORY_TOKEN`: langer zufälliger Zugangsschlüssel, z. B. mit `python -c 'import secrets; print(secrets.token_urlsafe(32))'` erzeugen.
- `DATABASE_URL`: optional, Standard SQLite im Backend-Arbeitsverzeichnis.
- `PROJECT_ROOT`: optional, Standard `backend/data/projects` bei obigem Start.

Ein Aufruflimit ist kein Geldbudget. Anbieterpreise variieren; zusätzlich beim Anbieter ein Ausgabenlimit setzen. Der vollständige Anforderungstext und erzeugte Dateien werden an den konfigurierten Anbieter gesendet. Keine geheimen Daten in Projektanweisungen eingeben. Fehlerantworten des Anbieters werden nicht mit potenziell sensiblen Rohdaten ausgegeben.

## Tests

```bash
cd backend
../.venv/bin/pytest -q
cd ../frontend
npm run build
```

Die automatisierten Orchestrierungstests verwenden ausdrücklich Test-Doubles; die produktive Anwendung besitzt keinen Fake-Provider. Ohne API-Schlüssel kann kein echter Modelllauf verifiziert werden.

## MVP-Grenzen und Erweiterungen

Implementiert: Modellaufrufe, kooperierende spezialisierte Agentenschritte, Revisionen, lokale Persistenz, Syntaxprüfung, Korrekturschleife, tatsächlicher Ereignisverlauf, ZIP, optionale eingeschränkte Laufzeittests, schreibgeschützte Codeansicht und HTML-Vorschau ohne Skripte.

Noch nicht implementiert: editierbarer Code-Editor, interaktive Vorschau beliebiger Full-Stack-Projekte, Deployment, automatische Paketinstallation, Fine-Tuning, belastbares Geldbudget, automatische Bewertung und Übernahme von Optimierungen, projektübergreifendes Lernen/Komponentenbibliothek, Rollenverwaltung und Multi-Tenant-Isolation. Historische Berichte werden gespeichert, aber nicht automatisch als erfolgreiche Lösungen gelernt. Änderungen werden durch neue Revisionen erhalten; ein UI-Rollback ist noch nicht vorhanden. Kein Produktbutton behauptet diese Funktionen.

Für öffentlichen Betrieb sind ein TLS-Reverse-Proxy, individuelle Benutzerzugänge, Rate-Limits, Backup, Secret-Management und isolierte Runner nötig. Dieser MVP ist eine private Einzelbenutzer-Entwicklungsplattform. Genau einen Backend-Worker verwenden, da die Aufgabenwarteschlange im Prozess lebt. Datenbank und Projektdateien gemeinsam sichern.
