# Color Formulation System

A production-grade web application for ink manufacturing companies to manage mixing bases,
generate Pantone formulations, and perform custom color matching using spectral color science.

## Architecture

```
Color-System/
├── backend/                 # Flask API server
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── api/             # REST API route handlers
│   │   ├── services/        # Business logic (formulation engine, CXF parser)
│   │   └── utils/           # Helpers (auth, file handling, color math)
│   ├── migrations/          # Alembic database migrations
│   └── tests/               # pytest test suite
├── frontend/                # React SPA
│   ├── public/
│   └── src/
│       ├── components/      # UI organized by domain
│       ├── services/        # API client layer
│       └── utils/           # Client-side helpers
├── scripts/                 # Setup, deployment, seed data
└── docs/                    # Additional documentation
```

## Tech Stack

| Layer        | Technology           | Rationale                                           |
|--------------|----------------------|-----------------------------------------------------|
| Backend      | Python 3.11+ / Flask | Best ecosystem for color science (NumPy, SciPy)     |
| Database     | PostgreSQL 15+       | JSONB for spectral data, robust relational model     |
| ORM          | SQLAlchemy 2.0       | Mature, supports complex queries and migrations      |
| Migrations   | Alembic              | Production-grade schema versioning                   |
| Auth         | Flask-Login + JWT    | Session auth for web, JWT for API                    |
| Frontend     | React 18             | Component model fits manufacturing workflow screens  |
| CSS          | Bootstrap 5          | Clean, professional UI without heavy customization   |
| Color Science| NumPy + SciPy        | Required for Kubelka-Munk and spectral optimization  |
| PDF Export   | ReportLab            | Production-quality PDF generation                    |
| Excel Export | openpyxl             | Native .xlsx generation                              |
| Deployment   | Gunicorn + Nginx     | Standard production Python deployment on Ubuntu      |

## Key Design Decisions

1. **Kubelka-Munk two-constant theory** for the formulation engine. This is the industry
   standard for predicting color of pigment mixtures. K/S values are additive, making
   formula optimization a constrained least-squares problem.

2. **Spectral data stored at 10nm intervals (360-780nm)** — 43 data points per measurement.
   This is the standard resolution for color formulation. Stored as JSONB arrays in PostgreSQL.

3. **Ink series are fully isolated** — bases, formulas, and matches are always scoped to a
   series. This matches how ink manufacturers actually organize their product lines.

4. **CXF parser is modular** — the parser extracts spectral reflectance data from CXF/X-4
   files (the most common variant for ink industry). Additional CXF schemas can be added
   as parser plugins.

5. **Formula history is immutable** — when bases are updated and formulas regenerated,
   old formula versions are preserved with full audit trail.

## Quick Start (Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Edit with your database credentials
flask db upgrade       # Run migrations
python seed.py         # Load example data
flask run              # Starts on http://localhost:5000
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
npm start              # Starts on http://localhost:3000
```

### Default Admin Account
- Email: admin@colorformulation.local
- Password: ChangeMe123!

## Production Deployment

See [docs/deployment.md](docs/deployment.md) for full Ubuntu Server deployment guide.

## CXF Support

The system currently supports **CXF/X-4** files containing spectral reflectance data.
See [docs/cxf-support.md](docs/cxf-support.md) for details on supported elements and
known limitations.

## Formulation Engine

The formulation engine uses Kubelka-Munk two-constant theory with constrained optimization.
See [docs/formulation-engine.md](docs/formulation-engine.md) for the mathematical model,
assumptions, and improvement roadmap.

## Assumptions

- Spectral data is reflectance factor (0.0–1.0) at 10nm intervals, 360–780nm
- CXF files follow CXF/X-4 schema with spectral reflectance data
- Kubelka-Munk two-constant theory is sufficient for initial formulations
- Pantone target spectral data must be imported separately (proprietary)
- All mixing is subtractive (ink on substrate), not additive (light)
- Substrate (white base / paper) spectral data is required for accurate formulation

## Known Limitations

- Single-constant Kubelka-Munk is used initially; two-constant requires transmission
  measurements that may not be in standard CXF files
- Metamerism detection is not yet implemented
- No automatic gamut mapping — out-of-gamut targets return best achievable match
- CXF namespace handling covers common variants but may need extension for some vendors
- Fluorescent colorants are not modeled
- Temperature and humidity effects on color are not modeled

## Data Dependencies

- **Pantone spectral data**: Must be imported from licensed Pantone libraries (not bundled)
- **Substrate spectral data**: Must be measured and uploaded per substrate type
- **Base K/S values**: Derived from uploaded spectral data at known concentrations against
  a known substrate

## Recommended Future Improvements

1. Two-constant Kubelka-Munk (requires transmission measurements)
2. Metamerism index calculation and illuminant comparison
3. Cost optimization in formula generation (minimize expensive pigments)
4. Batch formulation — generate all Pantone formulas for a series at once
5. Spectrophotometer direct integration (serial/USB)
6. Color library import from other standards (HKS, RAL, NCS)
7. Production batch tracking and QC measurement logging
8. Multi-substrate support with substrate-specific formulation
9. WebSocket-based real-time formulation progress for large batches
10. Mobile-friendly measurement entry for shop floor use
