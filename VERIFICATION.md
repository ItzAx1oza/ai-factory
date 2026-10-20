# Durchgeführte Prüfungen

- Backend: 13 pytest-Tests bestanden (eine Deprecation-Warnung in Starlette/AnyIO).
- Frontend: Produktionsbuild mit Next.js 16.4.2 einschließlich TypeScript-Prüfung erfolgreich.
- npm audit nach Aktualisierung: 0 gemeldete Schwachstellen.
- Echter Docker-Runner: ein Python-unittest in python:3.12-slim mit den implementierten Limits erfolgreich ausgeführt. Ein dabei gefundenes Dateirechteproblem wurde behoben.
- Docker-Compose-Konfiguration validiert. Der vollständige Compose-Stack und PostgreSQL wurden nicht gestartet.
- Kein echter Modellauftrag: Kein Modell-API-Schlüssel konfiguriert. Provider-HTTP-Vertrag und Agenten-Korrekturschleife wurden mit ausdrücklich gekennzeichneten Test-Doubles geprüft.
- Kein Browser-/iPhone-End-to-End-Test durchgeführt. Responsives CSS ist implementiert.
