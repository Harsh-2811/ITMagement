
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q , F
from .models import *
from api.dailytask.models import TaskTimeLog, DailyTask

TWOPLACES = Decimal("0.01")

def q2(v) -> Decimal:
    return (v if isinstance(v, Decimal) else Decimal(str(v))).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def accrue_monthly_leave(employee: Employee, as_of: date | None = None):
    """Accrue leave for all leave types for one month."""
    as_of = as_of or date.today()
    for lt in LeaveType.objects.all():
        lb, _ = LeaveBalance.objects.get_or_create(employee=employee, leave_type=lt)
        lb.balance = q2(lb.balance + lt.accrual_per_month)
        lb.save(update_fields=["balance", "updated_at"])


@transaction.atomic
def approve_leave(request_obj: LeaveRequest, manager_user):
    """Approve leave and deduct balance."""
    days = request_obj.duration_days()
    lb = LeaveBalance.objects.select_for_update().get(employee=request_obj.employee, leave_type=request_obj.leave_type)
    if lb.balance < days:
        raise ValueError("Insufficient leave balance")
    lb.balance = q2(lb.balance - days)
    lb.save(update_fields=["balance", "updated_at"])
    request_obj.status = LeaveRequest.Status.APPROVED
    request_obj.manager = manager_user
    request_obj.save(update_fields=["status", "manager", "decided_at"])


def reject_leave(request_obj: LeaveRequest, manager_user):
    request_obj.status = LeaveRequest.Status.REJECTED
    request_obj.manager = manager_user
    request_obj.save(update_fields=["status", "manager", "decided_at"])


def contracts_expiring_within(days=30):
    cutoff = date.today() + timedelta(days=days)
    return EmployeeContract.objects.filter(end_date__lte=cutoff, status=EmployeeContract.Status.ACTIVE)

def certifications_expiring_within(days=30):
    cutoff = date.today() + timedelta(days=days)
    return Certification.objects.filter(expiry_date__isnull=False, expiry_date__lte=cutoff)



@transaction.atomic
def generate_payslip_for_employee(run: PayrollRun, employee: Employee):
    cfg = PayrollConfig.objects.first()  
    base = q2(employee.base_salary)


    basic = q2(base * cfg.basic_percent / Decimal("100"))
    hra = q2(base * cfg.hra_percent / Decimal("100"))

    ot_hours = OvertimeRecord.objects.filter(
        employee=employee, date__gte=run.period_start, date__lte=run.period_end
    ).aggregate(total=Sum("hours"))["total"] or Decimal("0.00")
    overtime_pay = q2(ot_hours * cfg.overtime_hour_rate)

    gross = q2(basic + hra + overtime_pay)

    pf_emp = q2(basic * cfg.pf_employee_percent / Decimal("100"))
    esi_emp = q2(gross * cfg.esi_employee_percent / Decimal("100"))
    income_tax = q2(gross * cfg.income_tax_percent / Decimal("100")) 

    deductions = q2(pf_emp + esi_emp + income_tax)
    net = q2(gross - deductions)

    line_items = {
        "structure": {"basic": float(basic), "hra": float(hra)},
        "overtime": {"hours": float(ot_hours), "amount": float(overtime_pay)},
        "deductions": {
            "pf_employee": float(pf_emp),
            "esi_employee": float(esi_emp),
            "income_tax": float(income_tax),
        },
        "gross": float(gross),
        "net": float(net),
    }

    payslip, _ = Payslip.objects.update_or_create(
        payroll_run=run, employee=employee,
        defaults=dict(
            status=Payslip.Status.FINAL,
            gross=gross, basic=basic, hra=hra, overtime_pay=overtime_pay,
            pf_employee=pf_emp, esi_employee=esi_emp, income_tax=income_tax,
            other_deductions=Decimal("0.00"), net_pay=net, line_items=line_items
        )
    )
    return payslip


@transaction.atomic
def generate_payroll_run(period_start, period_end, processed_by):
    run = PayrollRun.objects.create(period_start=period_start, period_end=period_end, processed_by=processed_by)
    for emp in Employee.objects.filter(status=Employee.Status.ACTIVE):
        generate_payslip_for_employee(run, emp)
    return run



def q2(x):  
    return (x if isinstance(x, Decimal) else Decimal(str(x))).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def daterange_weeks(start: date, end: date):
    """Yield (wk_start, wk_end) tuples (Mon..Sun)."""
    cur = start
    while cur <= end:
        wk_start = cur - timedelta(days=cur.weekday())
        wk_end = wk_start + timedelta(days=6)
        yield max(wk_start, start), min(wk_end, end)
        cur = wk_end + timedelta(days=1)


def hours_logged(employee_id, start, end, project_id: int | None = None) -> Decimal:
    qs = TaskTimeLog.objects.filter(user_id=Employee.objects.get(id=employee_id).user_id,
                                    date__gte=start, date__lte=end)
    if project_id:
        qs = qs.filter(task__project_id=project_id)
    total = qs.aggregate(total=Sum("hours"))["total"] or Decimal("0.00")
    return q2(total)

def weekly_capacity_hours(
    employee_id,
    start,
    end,
    *,
    project_id: str | int | None = None,
    base_week_hours: Decimal = Decimal("40.00"),
    use_planned: bool = True,
) -> Decimal:
    """
    Capacity over [start,end]. If project_id is given, only include capacity earmarked for that project.
    If use_planned=True, use assignment.planned_hours_per_week * allocation%; otherwise fallback to base_week_hours * sum(allocation%).
    Prorates partial weeks by overlap days/7 and subtracts approved leave at (contract_week_hours/5) per day.
    """
    emp = Employee.objects.get(id=employee_id)
    total = Decimal("0.00")

    contract_week_hours = getattr(
        EmployeeContract.objects.filter(employee=emp, status=EmployeeContract.Status.ACTIVE).order_by("-start_date").first(),
        "weekly_hours",
    ) or base_week_hours


    leave_days = 0
    approved = LeaveRequest.objects.filter(
        employee=emp, status=LeaveRequest.Status.APPROVED,
        start_date__lte=end, end_date__gte=start
    )
    for lv in approved:
        s = max(lv.start_date, start); e = min(lv.end_date, end)
        leave_days += (e - s).days + 1
    leave_hours = Decimal(leave_days) * (Decimal(contract_week_hours) / Decimal("5"))

    assignments = ResourceAssignment.objects.filter(
        employee=emp, start_date__lte=end, end_date__gte=start
    )
    if project_id:
        assignments = assignments.filter(project_id=project_id)

    for wk_start, wk_end in daterange_weeks(start, end):
        overlap_start = max(wk_start, start); overlap_end = min(wk_end, end)
        days = (overlap_end - overlap_start).days + 1
        frac = Decimal(days) / Decimal("7")

        if use_planned:
            qs = assignments.filter(start_date__lte=wk_end, end_date__gte=wk_start)
            alloc = qs.aggregate(p=Sum("allocation_percent"))["p"] or Decimal("0")
            alloc = min(alloc, Decimal("100"))
            planned_sum = qs.aggregate(h=Sum("planned_hours_per_week"))["h"] or Decimal("0")
            week_cap = (Decimal(planned_sum) * (alloc / Decimal("100"))) * frac
        else:
            alloc = assignments.filter(start_date__lte=wk_end, end_date__gte=wk_start)\
                               .aggregate(p=Sum("allocation_percent"))["p"] or Decimal("0")
            alloc = min(alloc, Decimal("100"))
            week_cap = (Decimal(base_week_hours) * (alloc / Decimal("100"))) * frac

        total += week_cap

    total = q2(total - leave_hours)
    return total if total > 0 else Decimal("0.00")


def compute_utilization(employee_id, start, end, project_id=None):
    hours = hours_logged(employee_id, start, end, project_id=project_id)
    capacity = weekly_capacity_hours(employee_id, start, end, project_id=project_id, use_planned=True)
    util = q2((hours / capacity * 100) if capacity > 0 else 0)
    return {"hours": hours, "capacity": capacity, "util_percent": util}

def utilization_band(employees_qs, start, end, over_threshold=Decimal("100"), under_threshold=Decimal("60")):
    """
    Classify employees: over/under/optimal utilization.
    """
    over, under, optimal = [], [], []
    for emp in employees_qs:
        m = compute_utilization(emp.id, start, end)
        rec = {"employee_id": str(emp.id), "code": emp.employee_code, "name": emp.user.get_full_name() or emp.user.username,
               "hours": float(m["hours"]), "capacity": float(m["capacity"]), "util_percent": float(m["util_percent"])}
        if m["util_percent"] > over_threshold: over.append(rec)
        elif m["util_percent"] < under_threshold: under.append(rec)
        else: optimal.append(rec)
    return {"over": over, "under": under, "optimal": optimal}

def _date_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return not (a_end < b_start or b_end < a_start)

def _current_assignment_load_percent(employee_id, start, end) -> Decimal:
    """
    Sum allocation% across overlapping assignments per week and average it (capped at 100).
    Returns a percent (0..100).
    """
    weeks = list(daterange_weeks(start, end))
    if not weeks:
        return Decimal("0")

    assigns = ResourceAssignment.objects.filter(
        employee_id=employee_id, start_date__lte=end, end_date__gte=start
    )

    weekly_totals = []
    for wk_start, wk_end in weeks:
        pct = assigns.filter(start_date__lte=wk_end, end_date__gte=wk_start) \
                     .aggregate(p=Sum("allocation_percent"))["p"] or Decimal("0")
        weekly_totals.append(min(pct, Decimal("100")))
    avg = sum(weekly_totals, Decimal("0")) / Decimal(len(weekly_totals))
    return q2(avg)


def recommend_employees(
    project_id,
    requirements: list[dict],
    start: date,
    end: date,
    limit: int = 10,
    *,
    weights: dict | None = None,
    desired_hours_per_week: Decimal | None = None,
    exclude_heavily_booked: bool = False,
    heavy_booking_threshold_percent: Decimal = Decimal("90"),
):
    """
    Partial-match, weighted recommendations.

    requirements = [{"skill_id": "<uuid>", "min_level": 3}, ...]
    weights = {
      "skill_coverage": 0.45,   
      "skill_level_fit": 0.25,  
      "free_capacity": 0.20,    
      "utilization": 0.10,      
    }
    desired_hours_per_week: if not provided, inferred as 20.00
    exclude_heavily_booked: if True, filters out candidates whose avg overlapping allocation% >= threshold
    """
    if not requirements:
        return []

    weights = weights or {
        "skill_coverage": 0.45,
        "skill_level_fit": 0.25,
        "free_capacity": 0.20,
        "utilization": 0.10,
    }
    w_total = sum(weights.values())
    if w_total <= 0:
        weights = {k: (0 if k != "free_capacity" else 1.0) for k in weights} 
        w_total = 1.0
    norm_w = {k: float(v) / float(w_total) for k, v in weights.items()}

    desired_hours_per_week = q2(desired_hours_per_week or Decimal("20.00"))

    skill_ids = [r["skill_id"] for r in requirements]
    min_levels = {str(r["skill_id"]): int(r.get("min_level", 3)) for r in requirements}
    req_count = len(skill_ids)

    base_ids = EmployeeSkill.objects.filter(skill_id__in=skill_ids) \
                                    .values_list("employee_id", flat=True).distinct()

    results = []
    for emp in Employee.objects.filter(id__in=base_ids).select_related("user"):
        skills = list(EmployeeSkill.objects.filter(employee=emp, skill_id__in=skill_ids))
        have = {str(s.skill_id): s for s in skills}

        covered = sum(1 for sid in skill_ids if str(sid) in have)
        coverage = covered / req_count if req_count else 0.0

        fit_parts = []
        for sid in skill_ids:
            sid_str = str(sid)
            if sid_str in have:
                min_req = max(1, min_levels[sid_str])
                lvl = max(1, int(getattr(have[sid_str], "level", 1)))
                fit_parts.append(min(1.0, lvl / min_req))
        level_fit = (sum(fit_parts) / len(fit_parts)) if fit_parts else 0.0

        util = compute_utilization(emp.id, start, end) 
        free_capacity = float(max(Decimal("0.00"), util["capacity"] - util["hours"])) 
        free_capacity_score = float(min(1.0, (free_capacity / float(desired_hours_per_week))) if desired_hours_per_week > 0 else 0.0)

        util_percent = float(util["util_percent"])
        utilization_score = max(0.0, min(1.0, (100.0 - util_percent) / 100.0))

        if exclude_heavily_booked:
            avg_planned_pct = float(_current_assignment_load_percent(emp.id, start, end))
            if avg_planned_pct >= float(heavy_booking_threshold_percent):
                continue

        total_score = (
            norm_w["skill_coverage"] * coverage +
            norm_w["skill_level_fit"] * level_fit +
            norm_w["free_capacity"]   * free_capacity_score +
            norm_w["utilization"]     * utilization_score
        )

        results.append({
            "employee_id": str(emp.id),
            "name": emp.user.get_full_name() or emp.user.username,
            "employee_code": emp.employee_code,
            "skill_coverage": round(coverage, 4),
            "skill_level_fit": round(level_fit, 4),
            "free_capacity_hours": round(free_capacity, 2),
            "util_percent": round(util_percent, 2),
            "score": round(total_score, 6),
            "weights_used": norm_w,
            "details": {
                "desired_hours_per_week": float(desired_hours_per_week),
                "avg_planned_allocation_percent": float(_current_assignment_load_percent(emp.id, start, end)),
                "skills_present": [
                    {
                        "skill_id": str(s.skill_id),
                        "level": int(s.level),
                        "meets_min": (int(s.level) >= int(min_levels[str(s.skill_id)])),
                        "min_required": int(min_levels[str(s.skill_id)]),
                    }
                    for s in skills
                ],
            }
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]



def project_time_split(employee_id, start, end):
    """
    Cross-project split of actual hours.
    """
    emp = Employee.objects.get(id=employee_id)
    rows = (TaskTimeLog.objects.filter(user_id=emp.user_id, date__gte=start, date__lte=end)
            .values("task__project_id", "task__project__name")
            .annotate(hours=Sum("hours"))
            .order_by("-hours"))
    total = sum([r["hours"] for r in rows]) or 0
    out = []
    for r in rows:
        pct = float(Decimal(r["hours"]) * 100 / Decimal(total)) if total else 0.0
        out.append({
            "project_id": r["task__project_id"],
            "project_name": r["task__project__name"],
            "hours": float(r["hours"]),
            "percent": pct
        })
    return {"employee_id": str(emp.id), "employee_code": emp.employee_code, "split": out}


def forecast_gaps(project_id, start, end):
    demand_hours = Decimal("0.00")
    planned = Decimal("0.00")

    for wk_start, wk_end in daterange_weeks(start, end):
        overlap_start = max(wk_start, start); overlap_end = min(wk_end, end)
        days = (overlap_end - overlap_start).days + 1
        frac = Decimal(days) / Decimal("7")

        for rf in ResourceForecast.objects.filter(project_id=project_id, start_date__lte=wk_end, end_date__gte=wk_start):
            demand_hours += (rf.required_hours_per_week * rf.headcount) * frac

        for ra in ResourceAssignment.objects.filter(project_id=project_id, start_date__lte=wk_end, end_date__gte=wk_start):
            planned += (ra.planned_hours_per_week * (ra.allocation_percent / Decimal("100.00"))) * frac

    gap = q2(demand_hours - planned)
    return {"demand_hours": float(q2(demand_hours)), "planned_hours": float(q2(planned)), "gap_hours": float(gap)}
