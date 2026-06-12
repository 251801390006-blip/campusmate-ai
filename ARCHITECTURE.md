# CampusMate AI - Architecture Diagram

```mermaid
graph TD
    %% User & Edge layer
    User[Student/User] --> |HTTPS| Cloudflare[Cloudflare Edge / CDN]
    Cloudflare --> |Routing| Railway[Railway App Platform]
    
    %% Application Layer
    subgraph "CampusMate AI (Flask Monolith)"
        Railway --> AppRoute(Flask Router)
        
        %% Core Services
        AppRoute --> Auth[Authentication Service]
        AppRoute --> Resume[Resume Builder & ATS Engine]
        AppRoute --> Roadmap[Roadmap & Progress Engine]
        AppRoute --> Dashboard[Student Analytics Dashboard]
        
        %% Integrations
        Resume --> WeasyPrint(WeasyPrint PDF Generator)
        Resume --> RegexParser(Keyword/ATS Parser)
    end
    
    %% Data Layer
    subgraph "Data Persistence"
        Auth --> DB[(SQLite / PostgreSQL)]
        Resume --> DB
        Roadmap --> DB
        Dashboard --> DB
    end
```

### Stack Components
- **Frontend**: HTML5, Vanilla JavaScript, Bootstrap 5 CSS, Custom CSS (Glassmorphism UI)
- **Backend**: Python 3.10+, Flask Framework
- **Database**: SQLite (Development) / PostgreSQL ready
- **Rendering**: Jinja2 Templating
- **PDF Generation**: WeasyPrint / GTK
- **Deployment**: Railway
