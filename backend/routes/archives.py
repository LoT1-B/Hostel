# backend/routes/archives.py
"""API des archives mensuelles : archiver, rouvrir, re-archiver, consulter + rapport imprimable."""
import json
import html as html_mod
from datetime import date

from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required

from backend.models import db, Archive
from backend.archive_service import (
    build_snapshot, is_frozen, month_key, current_user, is_manager_user,
)

archives_bp = Blueprint("archives", __name__)


def _serialize(a):
    return {
        "id": a.id, "month": a.month, "status": a.status, "version": a.version,
        "createdBy": a.created_by, "createdAt": a.created_at.isoformat() if a.created_at else None,
        "openedAt": a.opened_at.isoformat() if a.opened_at else None,
        "openedBy": a.opened_by or "", "openedReason": a.opened_reason or "",
    }


@archives_bp.route("/api/archives", methods=["GET"])
@jwt_required()
def list_archives():
    rows = Archive.query.order_by(Archive.month.desc()).all()
    return jsonify([_serialize(a) for a in rows])


@archives_bp.route("/api/archives/<month>", methods=["GET"])
@jwt_required()
def get_archive(month):
    a = Archive.query.filter_by(month=month).first()
    if not a:
        return jsonify({"msg": "Ce mois n'est pas archivé"}), 404
    try:
        snap = json.loads(a.snapshot or "{}")
    except ValueError:
        snap = {}
    return jsonify({**_serialize(a), "snapshot": snap})


@archives_bp.route("/api/archives", methods=["POST"])
@jwt_required()
def create_archive():
    """Archive un mois passé terminé → le fige. Manager uniquement."""
    user = current_user()
    if not is_manager_user(user):
        return jsonify({"msg": "Accès refusé : manager requis pour archiver"}), 403

    data = request.get_json() or {}
    month = (data.get("month") or "").strip()
    if len(month) != 7 or month[4] != "-":
        return jsonify({"msg": "Mois invalide (format YYYY-MM)"}), 400

    try:
        y = int(month[:4]); m = int(month[5:7])
    except ValueError:
        return jsonify({"msg": "Mois invalide (format YYYY-MM)"}), 400
    if not (1 <= m <= 12):
        return jsonify({"msg": "Mois invalide"}), 400

    # On ne peut pas archiver le mois en cours (pas terminé) ni un mois futur
    today_month = date.today().strftime('%Y-%m')
    if month >= today_month:
        return jsonify({"msg": "Impossible d'archiver le mois en cours ou un mois futur"}), 400

    a = Archive.query.filter_by(month=month).first()
    if a and a.status == "frozen":
        return jsonify({"msg": "Ce mois est déjà archivé et figé"}), 409
    if a:
        return jsonify({"msg": "Ce mois est enregistré. Utilisez \"Ré-ouvrir\" puis \"Re-archiver\"."}), 409

    snap = build_snapshot(month)
    a = Archive(
        month=month, status="frozen", version=1,
        snapshot=json.dumps(snap, ensure_ascii=False),
        created_by=user.username,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(_serialize(a)), 201


@archives_bp.route("/api/archives/<month>/reopen", methods=["POST"])
@jwt_required()
def reopen_archive(month):
    """Ré-ouvre un mois archivé pour corriger une erreur. Manager uniquement."""
    user = current_user()
    if not is_manager_user(user):
        return jsonify({"msg": "Accès refusé : manager requis"}), 403
    a = Archive.query.filter_by(month=month).first()
    if not a:
        return jsonify({"msg": "Mois non archivé"}), 404
    if a.status == "active":
        return jsonify({"msg": "Ce mois est déjà ré-ouvert"}), 409
    data = request.get_json() or {}
    a.status = "active"
    a.opened_at = None  # mis à jour par le contexte (datetime) — voir attribution
    a.opened_by = user.username
    a.opened_reason = (data.get("reason") or "").strip()
    from datetime import datetime
    a.opened_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_serialize(a))


@archives_bp.route("/api/archives/<month>/close", methods=["POST"])
@jwt_required()
def close_archive(month):
    """Re-archivet un mois ré-ouvert (nouveau snapshot, version++). Manager uniquement."""
    user = current_user()
    if not is_manager_user(user):
        return jsonify({"msg": "Accès refusé : manager requis"}), 403
    a = Archive.query.filter_by(month=month).first()
    if not a:
        return jsonify({"msg": "Mois non archivé"}), 404
    if a.status == "frozen":
        return jsonify({"msg": "Ce mois est déjà figé"}), 409
    a.status = "frozen"
    a.version += 1
    a.opened_at = None; a.opened_by = ""; a.opened_reason = ""
    a.snapshot = json.dumps(build_snapshot(month), ensure_ascii=False)
    db.session.commit()
    return jsonify(_serialize(a))


@archives_bp.route("/api/archives/<month>/snapshot", methods=["GET"])
@jwt_required()
def get_snapshot(month):
    a = Archive.query.filter_by(month=month).first()
    if not a:
        return jsonify({"msg": "Ce mois n'est pas archivé"}), 404
    try:
        snap = json.loads(a.snapshot or "{}")
    except ValueError:
        snap = {}
    return jsonify(snap)


def _esc(x):
    return html_mod.escape(str(x))


@archives_bp.route("/api/archives/<month>/pdf", methods=["GET"])
@jwt_required()
def archive_pdf(month):
    """Renvoie un rapport HTML formaté A4, imprimable via window.print()."""
    a = Archive.query.filter_by(month=month).first()
    if not a:
        return jsonify({"msg": "Ce mois n'est pas archivé"}), 404
    try:
        snap = json.loads(a.snapshot or "{}")
    except ValueError:
        snap = {}
    st = snap.get("statistics", {})
    def rows(lst, cols):
        if not lst:
            return ""
        head = "".join(f"<th>{_esc(c)}</th>" for c in cols)
        body = ""
        for r in lst:
            body += "<tr>" + "".join(f"<td>{_esc(r.get(k, ''))}</td>" for k in cols) + "</tr>"
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Villa Blanca - Archive {_esc(month)}</title>
<style>
 body{{font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#111;margin:18px}}
 h1{{font-size:20px;margin:0 0 2px}} h2{{font-size:15px;border-bottom:1px solid #bbb;margin:18px 0 6px}}
 .sub{{color:#555;margin-bottom:8px}} .box{{display:inline-block;border:1px solid #999;padding:6px 10px;margin:4px 6px 4px 0;border-radius:4px;background:#f6f6f6}}
 table{{width:100%;border-collapse:collapse;margin:6px 0}}
 th,td{{border:1px solid #555;padding:4px 6px;text-align:left;font-size:10px}}
 th{{background:#e3e3e3}}
 footer{{margin-top:20px;font-size:9px;color:#777;text-align:right}}
 .noprint{{margin:6px 0}}
</style></head><body>
<button class="noprint" onclick="window.print()">🫙 Imprimer / Enregistrer en PDF</button>
<h1>Villa Blanca — Archive mensuelle</h1>
<div class="sub">Mois : <b>{_esc(month)}</b> ({_esc(snap.get('period',''))}) — Version v{a.version} • archivé le {_esc(a.created_at.isoformat() if a.created_at else '')} par {_esc(a.created_by)}</div>

<h2>Résumé</h2>
<div class="box">Chambres (fin) : <b>{st.get('nb_chambres_a_la_fin', 0)}</b></div>
<div class="box">Réservations : <b>{st.get('reservations', 0)}</b></div>
<div class="box">Bons : <b>{st.get('bons', 0)}</b> (dont {st.get('bons_encaisse', 0)} encaissés)</div>
<div class="box">Caisse encaissée : <b>{st.get('caisse_encaisse', 0)} F</b></div>
<div class="box">Bénéfice : <b>{st.get('caisse_benefice', 0)} F</b></div>
<div class="box">Mouvements stock : <b>{st.get('mouvements', 0)}</b></div>

<h2>Réservations</h2>
{rows(snap.get('reservations', []), ['guest','room','checkin','checkout','status'])}

<h2>Bons de caisse</h2>
{rows([{'label': b.get('label'), 'category': b.get('category'), 'montant': b.get('montant'), 'cout': b.get('cout'), 'status': b.get('status'), 'day': b.get('day')} for b in snap.get('bons', [])], ['label','category','montant','cout','status','day'])}

<h2>Clôtures journalières</h2>
{rows(snap.get('closed_days', []), ['day','occupied','rooms_total','occupancy_rate','revenue','arrivals','departures','caisse_encaisse','caisse_benefice'])}

<h2>Mouvements de stock</h2>
{rows(snap.get('movements', []), ['date','type','item','qty','note'])}

<h2>Stock à la fin du mois</h2>
{rows(snap.get('stock_final', []), ['name','category','qty','unit','threshold'])}

<footer>Document généré le {_esc(date.today().isoformat())} — Villa Blanca / Hostel</footer>
</body></html>"""
    return Response(html, mimetype="text/html")