# Portale prima nota

Servizio indipendente da pubblicare da questa cartella come applicazione Docker, con un dominio HTTPS dedicato. L'hosting statico può pubblicare le pagine esistenti, mentre il portale richiede un servizio che esegua Python. Impostare una limitazione delle richieste al proxy di ingresso e consentire SMTP TLS in uscita verso il provider scelto.

1. Eseguire `python3 password.py` su un computer fidato. Comunicare la password all'utente attraverso un canale privato. Il nome utente è `prima-nota`.
2. Configurare nel pannello privato dell'hosting `PORTAL_PASSWORD_HASH` (l'hash generato), `PORTAL_ORIGIN` (es. `https://prima-nota.example.com`, senza barra finale), `SMTP_HOST`, `SMTP_PORT` (465 per impostazione predefinita), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` e `PRIMA_NOTA_TO` (casella di David). Usare un account di invio dedicato con credenziali SMTP. Il server ascolta su `PORT` (8080 se assente).
3. Verificare la ricezione con tre file fittizi. Creare una regola nella casella destinataria che filtri per mittente SMTP e oggetto `Prima nota |` e applichi l'etichetta **Prima nota**.

I file vengono inoltrati come allegati e trattati in memoria durante la richiesta. La conferma indica che il servizio SMTP ha accettato il messaggio. Il portale gestisce la raccolta; la riconciliazione contabile si avvia a parte. Tenere password, hash, file contabili e impostazioni di produzione fuori da Git.
