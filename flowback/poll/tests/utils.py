from django.utils import timezone


# Generates kwargs for Poll to match the given phase
def generate_poll_phase_kwargs(poll_start_phase: str) -> dict:
    match poll_start_phase:
        case 'waiting':
            poll_offset_hours = -1
        case 'area_vote':
            poll_offset_hours = 0
        case 'proposal':
            poll_offset_hours = 1
        case 'prediction_statement':
            poll_offset_hours = 2
        case 'prediction_bet':
            poll_offset_hours = 3
        case 'delegate_vote':
            poll_offset_hours = 4
        case 'vote':
            poll_offset_hours = 5
        case 'result':
            poll_offset_hours = 6
        case 'prediction_vote':
            poll_offset_hours = 7
        case _:
            poll_offset_hours = 0

    def phase(hour: int): return timezone.now() + timezone.timedelta(hours=hour - poll_offset_hours)

    return dict(start_date=phase(0),
                area_vote_end_date=phase(1),
                proposal_end_date=phase(2),
                prediction_statement_end_date=phase(3),
                prediction_bet_end_date=phase(4),
                delegate_vote_end_date=phase(5),
                vote_end_date=phase(6),
                end_date=phase(7))
