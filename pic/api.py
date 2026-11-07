"""JSON endpoints used by the public site."""
from flask import Blueprint, jsonify, request

from . import gemini
from .extensions import db
from .models import ServiceFitQuery
from .security import rate_limited

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/service-fit', methods=['POST'])
def service_fit():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    description = str(data.get('description') or '').strip()

    if not description:
        return jsonify({'error': 'Please describe your business situation first.'}), 400
    if len(description) > 500:
        return jsonify({'error': 'Please keep your description under 500 characters.'}), 400
    if rate_limited(('service-fit', request.remote_addr), limit=5, window_seconds=60):
        return jsonify({'error': "You're going a bit fast. Please wait a minute and try again."}), 429

    result = gemini.ask_gemini(gemini.service_fit_prompt(description))

    db.session.add(ServiceFitQuery(
        description=description,
        recommendation=result,
        suggested=','.join(gemini.detect_services(result)) or None,
        ok=result is not None,
    ))
    db.session.commit()

    if result is None:
        return jsonify({'error': 'Our assistant is temporarily busy. Please try again in a moment.'}), 503
    return jsonify({'recommendation': result})
