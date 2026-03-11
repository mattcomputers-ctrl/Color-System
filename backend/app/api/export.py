"""Export API endpoints for PDF and Excel downloads."""

from flask import Blueprint, request, jsonify, send_file
import io

from app import db
from app.models.pantone import PantoneFormula
from app.models.custom_match import CustomMatchJob
from app.utils.auth import login_required, get_current_user
from app.utils.export import generate_formula_pdf, generate_formula_excel

export_bp = Blueprint('export', __name__)


@export_bp.route('/pantone-formula/<int:formula_id>/pdf', methods=['GET'])
@login_required
def export_pantone_pdf(formula_id):
    """Export a Pantone formula as PDF."""
    formula = db.session.get(PantoneFormula, formula_id)
    if not formula:
        return jsonify({'error': 'Formula not found'}), 404

    target = formula.target
    formula_data = {
        'title': f'Pantone {target.pantone_code} Formula',
        'series_name': formula.series.name if formula.series else 'N/A',
        'version': formula.version,
        'created_at': formula.created_at.strftime('%Y-%m-%d %H:%M') if formula.created_at else '',
        'status': formula.status,
        'predicted_lab': formula.predicted_lab,
        'delta_e_2000': formula.delta_e_2000,
        'delta_e_76': formula.delta_e_76,
        'components': [c.to_dict() for c in formula.components],
        'notes': formula.notes,
    }
    target_data = {
        'code': target.pantone_code,
        'name': target.pantone_name or target.pantone_code,
        'lab_values': target.lab_values,
    }

    pdf_bytes = generate_formula_pdf(formula_data, target_data)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'formula_{target.pantone_code}_{formula.series.code}_v{formula.version}.pdf',
    )


@export_bp.route('/pantone-formulas/excel', methods=['GET'])
@login_required
def export_pantone_excel():
    """Export Pantone formulas as Excel."""
    query = PantoneFormula.query.filter_by(is_current=True)

    series_id = request.args.get('series_id', type=int)
    if series_id:
        query = query.filter_by(series_id=series_id)

    formulas = query.order_by(PantoneFormula.created_at.desc()).limit(500).all()

    formula_dicts = []
    for f in formulas:
        fd = f.to_dict()
        fd['target_code'] = f.target.pantone_code if f.target else ''
        fd['series_name'] = f.series.name if f.series else ''
        formula_dicts.append(fd)

    excel_bytes = generate_formula_excel(formula_dicts)
    return send_file(
        io.BytesIO(excel_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='pantone_formulas.xlsx',
    )


@export_bp.route('/custom-match/<int:job_id>/pdf', methods=['GET'])
@login_required
def export_custom_match_pdf(job_id):
    """Export a custom match job as PDF."""
    job = db.session.get(CustomMatchJob, job_id)
    if not job:
        return jsonify({'error': 'Match job not found'}), 404

    best = job.best_result
    formula_data = {
        'title': f'Custom Color Match — {job.job_name or f"Job #{job.id}"}',
        'series_name': job.series.name if job.series else 'N/A',
        'version': 1,
        'created_at': job.created_at.strftime('%Y-%m-%d %H:%M') if job.created_at else '',
        'status': job.status,
        'predicted_lab': best.predicted_lab if best else None,
        'delta_e_2000': best.delta_e_2000 if best else None,
        'delta_e_76': best.delta_e_76 if best else None,
        'components': [c.to_dict() for c in best.components] if best else [],
        'notes': job.notes,
    }
    target_data = {
        'code': job.job_name or f'Job #{job.id}',
        'name': f'{job.customer_name or ""} {job.project_name or ""}'.strip() or 'Custom Target',
        'lab_values': job.target_lab,
    }

    pdf_bytes = generate_formula_pdf(formula_data, target_data)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'custom_match_{job.id}.pdf',
    )
