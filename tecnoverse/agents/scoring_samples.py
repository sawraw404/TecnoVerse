"""SIMULATED sample data for trying the scoring matrix without the profiler or monitors.

Every company and opportunity here is made up and carries simulated=True.
Run from tecnoverse/:  python -m agents.scoring_samples
"""
from datetime import date, datetime, timezone

from core.schemas import Company, Opportunity, ProfileItem

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def item(company_id: str, field: str, value: str, status: str = "fact", visibility: str = "public",
         n: int = 0) -> ProfileItem:
    return ProfileItem(id=f"{company_id}-{field}-{n}", company_id=company_id, field=field, value=value,
                       status=status, visibility=visibility, updated_at=NOW,
                       quote_verified=status == "fact", confidence=0.9 if status == "fact" else 0.4)


SENSOR = Company(id="sim-sensor", name="SensorCo (SIMULATED)", website="https://example.com/sensor",
                 simulated=True)
CLOUD = Company(id="sim-cloud", name="CloudCo (SIMULATED)", website="https://example.com/cloud",
                simulated=True)
MARINE = Company(id="sim-marine", name="MarineCo (SIMULATED)", website="https://example.com/marine",
                 is_member=False, simulated=True)

ITEMS = {
    SENSOR.id: [
        item(SENSOR.id, "offering", "Vibration sensors for industrial pumps"),
        item(SENSOR.id, "technology", "Wireless sensor networks", n=1),
        item(SENSOR.id, "application_area", "Predictive maintenance in manufacturing"),
        item(SENSOR.id, "market", "Process industry"),
        item(SENSOR.id, "geography", "Head office in Karlskrona"),
    ],
    CLOUD.id: [
        item(CLOUD.id, "offering", "Cloud hosting and data storage"),
        item(CLOUD.id, "technology", "Kubernetes cloud platform"),
        item(CLOUD.id, "expertise", "Data security and sensor data pipelines"),
        item(CLOUD.id, "market", "Public sector"),
        item(CLOUD.id, "geography", "Offices in Ronneby"),
    ],
    MARINE.id: [
        item(MARINE.id, "offering", "Offshore wave energy converters"),
        item(MARINE.id, "application_area", "Marine renewable energy"),
        item(MARINE.id, "market", "Energy utilities", status="inferred"),
        item(MARINE.id, "geography", "Nordic countries"),
    ],
}


def opp(id: str, type: str, title: str, summary: str, **kw) -> Opportunity:
    return Opportunity(id=id, type=type, title=title, summary=summary, url=f"https://example.com/{id}",
                       source="curated", retrieved_at=NOW, simulated=True, **kw)


OPPORTUNITIES = [
    opp("t-sensor-lab", "testbed", "Industrial sensor test lab",
        "Testbed for validating vibration and wireless sensor solutions in manufacturing.",
        location="Karlskrona", contact="lab@example.com"),
    opp("e-cloud-day", "event", "Cloud security day",
        "Webinar on cloud platform security and data storage for the public sector.",
        format="online", start_date=date(2026, 12, 3)),
    opp("f-energy-call", "funding", "Call: marine renewable energy pilots",
        "Funding for offshore energy and wave energy pilots.",
        deadline=date(2027, 2, 1), requirements=["Swedish SME", "Partner from academia"]),
    opp("f-maintenance-call", "funding", "Call: predictive maintenance in industry",
        "Funding for predictive maintenance and sensor projects in the process industry.",
        deadline=date(2027, 1, 15), requirements=["Swedish company"]),
    opp("e-stockholm-expo", "event", "Industry expo Stockholm",
        "Trade fair for manufacturing and process industry suppliers.",
        format="in_person", location="Stockholm", start_date=date(2027, 3, 10)),
]


def _print_rankings() -> None:
    from agents.scoring import rank_connections, rank_opportunities

    print("SIMULATED sample data\n")
    for company in (SENSOR, CLOUD, MARINE):
        print(f"== {company.name}")
        for s in rank_opportunities(company, ITEMS[company.id], OPPORTUNITIES):
            b = s.breakdown
            print(f"  {s.match.rank}. {b['final']:.2f}  {s.title}"
                  f"   [topic {b['topic']:.2f} prio {b['priority']:.0f} region {b['region']:.1f}"
                  f" evid {b['evidence']:.2f}]")
        print()

    print("== Suggested connections (public items only)")
    for c in rank_connections([(c, ITEMS[c.id]) for c in (SENSOR, CLOUD, MARINE)]):
        print(f"  {c.breakdown['final']:.2f}  {c.names[0]} <-> {c.names[1]}")
        for basis in c.connection.basis:
            print(f"        - {basis.text}")
        print(f"        {c.connection.label}")


if __name__ == "__main__":
    _print_rankings()
