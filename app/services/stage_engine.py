"""
Where a student is in their programme, and what that means, in plain words.
Every figure comes from the student's own results; no university rules are assumed.
"""
from app.utils.grading import get_classification, truncate_gpa

GRADE_C = 1.5


def _projected(points: float, credits: int, add_credits: int, grade_point: float) -> float:
    return truncate_gpa(points + grade_point * add_credits, credits + add_credits)


def academic_stage(enrollment, points, credits, cgpa, classification, next_band, estimate, remaining) -> dict:
    award = enrollment.award_type
    award_word = "diploma" if award == "diploma" else "degree"
    is_top_up = award == "degree" and enrollment.entry_level > 100
    done, total = estimate["semesters_done"], estimate["total_semesters"]
    per_semester = estimate["average_credits_per_semester"]
    level = enrollment.current_level
    others = [e for e in enrollment.student.enrollments if e.id != enrollment.id]
    diploma_done = next((e for e in others if e.award_type == "diploma" and e.status == "completed"), None)

    stage = {
        "key": None,
        "title": "",
        "label": f"{done} of {total} semesters recorded",
        "messages": [],
        "semesters_done": done,
        "total_semesters": total,
        "next_semester": None,
        "finish": None,
    }
    say = stage["messages"].append

    # A finished programme the student has moved on from
    if enrollment.status == "completed" and not enrollment.is_current:
        stage.update(key="completed_programme", title=f"Completed {award_word}")
        if credits:
            say(f"This programme is finished. Its CGPA ({cgpa:.2f}) and class ({classification}) are final.")
        else:
            say("This programme is finished. Add its results to keep a full record.")
        return stage

    # No results yet
    if not credits:
        if is_top_up:
            stage.update(key="top_up_start", title=f"Starting your top-up at Level {enrollment.entry_level}")
            say("Your degree CGPA starts fresh. Your first semester sets your starting point.")
        else:
            stage.update(key="not_started", title=f"Starting your {award_word}")
            say("Your first semester sets your starting point. Add your results as soon as they are out.")
        if diploma_done:
            say("Your diploma is kept separately in your academic history.")
        return stage

    # Every semester of the programme recorded
    if estimate["remaining_semesters"] == 0:
        stage.update(key="complete", title=f"All semesters of your {award_word} recorded")
        say(f"You finished with {classification} ({cgpa:.2f}). This is final unless a result changes.")
        if award == "diploma" and not any(e.award_type == "degree" for e in others):
            say("Topping up to a degree? Add it from your Profile. Your diploma result stays in your history.")
        return stage

    best = _projected(points, credits, per_semester, 4.0)
    with_c = _projected(points, credits, per_semester, GRADE_C)
    stage["next_semester"] = {
        "credits": per_semester,
        "best": best,
        "best_class": get_classification(best, award),
        "with_c": with_c,
        "with_c_class": get_classification(with_c, award),
    }

    # Last year: show where the programme can still finish
    if estimate["remaining_semesters"] <= 2:
        left = remaining or estimate["remaining_credits"]
        top = _projected(points, credits, left, 4.0)
        low = _projected(points, credits, left, GRADE_C)
        stage["finish"] = {
            "remaining_credits": left,
            "best": top,
            "best_class": get_classification(top, award),
            "with_c": low,
            "with_c_class": get_classification(low, award),
        }
        stage.update(key="final", title=f"Final year of your {award_word}")
        say(
            f"About {left} credits left. The best you can finish on is {top:.2f} ({get_classification(top, award)}). "
            f"Averaging C from here would leave you at {low:.2f} ({get_classification(low, award)})."
        )
        if next_band:
            if top >= next_band["min"]:
                say(f"{next_band['label']} is still possible, but it needs strong grades from here.")
            else:
                say(f"{next_band['label']} is now out of reach, so focus on holding {classification}.")
        return stage

    first_year = done < 2
    if is_top_up and first_year:
        stage.update(key="early", title=f"First year of your top-up (Level {level})")
    elif first_year:
        stage.update(key="early", title=f"First year of your {award_word}")
    else:
        stage.update(key="middle", title=f"Level {level} of your {award_word}")

    range_text = f"Next semester could take it anywhere from {with_c:.2f} (all C's) to {best:.2f} (all A's)."
    if first_year:
        say("Your CGPA can still move a lot. " + range_text)
    else:
        say("Each semester now moves your CGPA a little less. " + range_text
            + " Steady grades matter more than one great semester.")
    if is_top_up and first_year and diploma_done:
        say(f"Your degree CGPA started fresh. Your {diploma_done.programme} result is kept separately.")
    return stage
