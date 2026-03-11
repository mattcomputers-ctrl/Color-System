"""Seed script to populate the database with initial data.

Run: python seed.py
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.user import User, Role
from app.models.series import InkSeries
from app.models.base import MixingBase, MixingBaseConcentration, BaseSpectralData
from app.models.pantone import PantoneTarget
from app.services.color_science import spectral_to_lab, reflectance_to_ks


def seed():
    app = create_app()
    with app.app_context():
        print('Seeding database...')

        # Create roles
        roles = {}
        for name, desc in [
            ('admin', 'Full system access'),
            ('formulator', 'Can create formulas, manage bases and series'),
            ('viewer', 'Read-only access to formulas and data'),
        ]:
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name, description=desc,
                            permissions='all' if name == 'admin' else name)
                db.session.add(role)
            roles[name] = role

        db.session.flush()

        # Create default admin user
        admin = User.query.filter_by(email='admin@colorformulation.local').first()
        if not admin:
            admin = User(
                email='admin@colorformulation.local',
                username='admin',
                first_name='System',
                last_name='Administrator',
                role_id=roles['admin'].id,
            )
            admin.set_password('ChangeMe123!')
            db.session.add(admin)
            print('  Created admin user: admin@colorformulation.local / ChangeMe123!')

        # Create sample formulator user
        formulator = User.query.filter_by(email='formulator@colorformulation.local').first()
        if not formulator:
            formulator = User(
                email='formulator@colorformulation.local',
                username='formulator',
                first_name='Sample',
                last_name='Formulator',
                role_id=roles['formulator'].id,
            )
            formulator.set_password('ChangeMe123!')
            db.session.add(formulator)
            print('  Created formulator user')

        db.session.flush()

        # Create sample ink series
        series_data = [
            ('UV-OFFSET', 'UV Offset Process Series',
             'UV-curable offset printing inks for sheet-fed and web applications'),
            ('CONV-OFFSET', 'Conventional Offset Series',
             'Oil-based conventional offset printing inks'),
            ('FLEXO-WB', 'Flexo Water-Based Series',
             'Water-based flexographic printing inks'),
        ]

        series_map = {}
        for code, name, desc in series_data:
            s = InkSeries.query.filter_by(code=code).first()
            if not s:
                s = InkSeries(code=code, name=name, description=desc, created_by_id=admin.id)
                db.session.add(s)
            series_map[code] = s

        db.session.flush()

        # Create sample mixing bases with synthetic spectral data
        # These are EXAMPLE spectral curves — real data must be measured and uploaded
        base_definitions = [
            # (code, name, color_index, synthetic_reflectance_generator)
            ('W', 'White', None, lambda wl: 0.88 + 0.02 * np.sin(wl / 100)),
            ('Y', 'Yellow', 'PY 13', lambda wl: np.where(wl < 500, 0.05 + 0.01 * (wl - 360) / 140,
                                                          0.75 + 0.1 * np.sin((wl - 500) / 50))),
            ('R', 'Warm Red', 'PR 57:1', lambda wl: np.where(wl > 600, 0.65 + 0.1 * (wl - 600) / 180,
                                                              0.04 + 0.02 * np.sin(wl / 80))),
            ('B', 'Blue', 'PB 15:3', lambda wl: np.where((wl > 420) & (wl < 520),
                                                          0.35 + 0.15 * np.sin((wl - 420) / 30),
                                                          0.03 + 0.02 * (wl > 600).astype(float))),
            ('G', 'Green', 'PG 7', lambda wl: np.where((wl > 490) & (wl < 580),
                                                        0.30 + 0.15 * np.sin((wl - 490) / 30),
                                                        0.03 + 0.01 * np.sin(wl / 60))),
            ('BK', 'Black', 'PBk 7', lambda wl: 0.04 + 0.005 * np.sin(wl / 200)),
            ('V', 'Violet', 'PV 23', lambda wl: np.where((wl > 380) & (wl < 460),
                                                          0.20 + 0.15 * np.sin((wl - 380) / 25),
                                                          0.03 + 0.02 * (wl > 640).astype(float))),
            ('O', 'Orange', 'PO 34', lambda wl: np.where(wl > 560,
                                                          0.50 + 0.2 * np.sin((wl - 560) / 40),
                                                          0.04 + 0.03 * np.sin(wl / 60))),
            ('TL', 'Transparent White (Letdown)', None, lambda wl: 0.92 + 0.01 * np.sin(wl / 150)),
        ]

        wavelengths = np.arange(360, 781, 10, dtype=float)

        for series_code in ['UV-OFFSET']:
            series = series_map[series_code]

            for code, name, ci, gen_func in base_definitions:
                base = MixingBase.query.filter_by(series_id=series.id, code=code).first()
                if base:
                    continue

                base = MixingBase(
                    series_id=series.id,
                    code=code,
                    name=name,
                    color_index=ci,
                    notes=f'Sample base — synthetic spectral data for demonstration only',
                    created_by_id=admin.id,
                )
                db.session.add(base)
                db.session.flush()

                # Add 100% concentration
                conc = MixingBaseConcentration(
                    base_id=base.id,
                    concentration_pct=100.0,
                    label='Full Strength',
                )
                db.session.add(conc)
                db.session.flush()

                # Generate synthetic spectral data
                reflectance = np.clip(gen_func(wavelengths), 0.005, 0.995)
                lab = spectral_to_lab(reflectance)
                ks = reflectance_to_ks(reflectance)

                spectral = BaseSpectralData(
                    concentration_id=conc.id,
                    version=1,
                    spectral_reflectance=reflectance.tolist(),
                    lab_l=float(lab[0]),
                    lab_a=float(lab[1]),
                    lab_b=float(lab[2]),
                    ks_values=ks.tolist(),
                    is_current=True,
                    created_by_id=admin.id,
                    notes='Synthetic data — for demonstration only',
                )
                db.session.add(spectral)

                print(f'  Created base {series_code}/{code} ({name}) '
                      f'L*={lab[0]:.1f} a*={lab[1]:.1f} b*={lab[2]:.1f}')

        # Load complete Pantone color library (Coated, Uncoated, Pastels & Neons)
        from pantone_data import PANTONE_COLORS

        added = 0
        for code, name, library, l, a, b in PANTONE_COLORS:
            existing = PantoneTarget.query.filter_by(pantone_code=code, library=library).first()
            if not existing:
                target = PantoneTarget(
                    pantone_code=code,
                    pantone_name=name,
                    library=library,
                    lab_l=l,
                    lab_a=a,
                    lab_b=b,
                    source='Community-reference LAB approximations. '
                           'Import official Pantone data for production use.',
                )
                db.session.add(target)
                added += 1

        print(f'  Loaded {added} new Pantone targets '
              f'({len(PANTONE_COLORS)} total in library)')

        db.session.commit()
        print('Seed data loaded successfully.')


if __name__ == '__main__':
    seed()
