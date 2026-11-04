"""Load the sample firm when the matter table is empty.

PostgreSQL installs that already ran database/law_firm_schema.sql are left alone.
The sample is demonstration data, not a training corpus.
"""
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from .core.security import get_password_hash
from .models.models import (
    PracticeGroup, PincodeArea, Location, Court, Lawyer, Client, OpposingParty,
    LegalCase, CaseLawyer, CaseClient, CaseOpposingParty, MatterType, StatuteSection,
    Evidence, CaseStatusAudit, ClientPhoneNo, OpposingPartyPhoneNo,
)
from .models.user import User


def seed_if_empty(db: Session) -> None:
    if db.query(LegalCase).first():
        return

    groups = [
        PracticeGroup(group_id=1, group_name="Criminal Litigation", description="Trials, bail, and criminal appeals", email="criminal@sample-chambers.test", contactno="08040001001"),
        PracticeGroup(group_id=2, group_name="Civil Litigation", description="Property, contract, and injunctions", email="civil@sample-chambers.test", contactno="08040001002"),
        PracticeGroup(group_id=3, group_name="Family Law", description="Marriage, maintenance, and custody", email="family@sample-chambers.test", contactno="08040001003"),
        PracticeGroup(group_id=4, group_name="Corporate Disputes", description="Shareholder and tribunal work", email="corporate@sample-chambers.test", contactno="08040001004"),
    ]
    pincodes = [
        PincodeArea(pincode="560001", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
        PincodeArea(pincode="560009", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
        PincodeArea(pincode="560011", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
        PincodeArea(pincode="560024", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
        PincodeArea(pincode="560025", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
        PincodeArea(pincode="560038", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
        PincodeArea(pincode="560058", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
        PincodeArea(pincode="560066", city="Bengaluru", district="Bengaluru Urban", state="Karnataka"),
    ]
    locations = [
        Location(location_id=1, landmark="MG Road commercial complex", streetno="12", pincode="560001"),
        Location(location_id=2, landmark="Jayanagar 4th Block", streetno="27", pincode="560011"),
        Location(location_id=3, landmark="Whitefield IT campus", streetno="4", pincode="560066"),
        Location(location_id=4, landmark="Indiranagar 100 Feet Road", streetno="100", pincode="560038"),
        Location(location_id=5, landmark="Hebbal residential layout", streetno="8", pincode="560024"),
        Location(location_id=6, landmark="Peenya industrial estate", streetno="2", pincode="560058"),
    ]
    courts = [
        Court(court_id=1, court_name="City Civil Court, Bengaluru", court_type="City Civil Court", pincode="560009"),
        Court(court_id=2, court_name="Chief Metropolitan Magistrate Court, Bengaluru", court_type="Magistrate Court", pincode="560001"),
        Court(court_id=3, court_name="High Court of Karnataka", court_type="High Court", pincode="560001"),
        Court(court_id=4, court_name="Debt Recovery Tribunal, Bengaluru", court_type="Tribunal", pincode="560025"),
    ]
    lawyers = [
        Lawyer(lawyer_id=1, fname="Ananya", lname="Rao", designation="Partner", phoneno="9845000001", bar_id="KAR/1234/2012", group_id=1),
        Lawyer(lawyer_id=2, fname="Vikram", lname="Iyer", designation="Senior Associate", phoneno="9845000002", bar_id="KAR/5678/2016", group_id=1),
        Lawyer(lawyer_id=3, fname="Meera", lname="Nair", designation="Partner", phoneno="9845000003", bar_id="KAR/2345/2011", group_id=2),
        Lawyer(lawyer_id=4, fname="Rohan", lname="Desai", designation="Associate", phoneno="9845000004", bar_id="KAR/8901/2019", group_id=2),
        Lawyer(lawyer_id=5, fname="Farah", lname="Khan", designation="Partner", phoneno="9845000005", bar_id="KAR/3456/2014", group_id=3),
        Lawyer(lawyer_id=6, fname="Arjun", lname="Menon", designation="Associate", phoneno="9845000006", bar_id="KAR/9012/2020", group_id=4),
    ]
    clients = [
        Client(client_id=1, fname="Lakshmi", lname="Prasad", email="lakshmi.prasad@example.test", address="Jayanagar, Bengaluru", sex="F", notes="Property owner. Prefers email updates."),
        Client(client_id=2, fname="Suresh", lname="Bhat", email="suresh.bhat@example.test", address="Rajajinagar, Bengaluru", sex="M", notes="Cheque-dishonour complainant."),
        Client(client_id=3, fname="Nalini", lname="George", email="nalini.george@example.test", address="Hebbal, Bengaluru", sex="F", notes="Maintenance petition."),
        Client(client_id=4, fname="Helios Components", lname="Pvt Ltd", email="legal@helios.example.test", address="Whitefield, Bengaluru", sex="O", notes="Corporate client."),
        Client(client_id=5, fname="Imran", lname="Qureshi", email="imran.q@example.test", address="Shivajinagar, Bengaluru", sex="M", notes="Bail already granted."),
        Client(client_id=6, fname="Divya", lname="Shetty", email="divya.shetty@example.test", address="Indiranagar, Bengaluru", sex="F", notes="Dissolution petition."),
        Client(client_id=7, fname="Northwind", lname="Traders", email="ops@northwind.example.test", address="Peenya, Bengaluru", sex="O", notes="Supply contract dispute."),
        Client(client_id=8, fname="Kiran", lname="Joshi", email="kiran.joshi@example.test", address="Malleshwaram, Bengaluru", sex="M", notes="Minority shareholder."),
    ]
    parties = [
        OpposingParty(party_id=1, fname="Ravi", lname="Hegde", email="ravi.hegde@example.test", address="Basavanagudi, Bengaluru", sex="M", repeat_party=False),
        OpposingParty(party_id=2, fname="Oasis Retail", lname="Pvt Ltd", email="notices@oasis.example.test", address="MG Road, Bengaluru", sex="O", repeat_party=True),
        OpposingParty(party_id=3, fname="Prakash", lname="George", email="prakash.george@example.test", address="Hebbal, Bengaluru", sex="M", repeat_party=True),
        OpposingParty(party_id=4, fname="State", lname="Prosecution", address="Bengaluru", sex="O", repeat_party=True),
        OpposingParty(party_id=5, fname="Aditya", lname="Shetty", email="aditya.shetty@example.test", address="Indiranagar, Bengaluru", sex="M", repeat_party=False),
        OpposingParty(party_id=6, fname="Summit", lname="Alloys", email="accounts@summit.example.test", address="Peenya, Bengaluru", sex="O", repeat_party=False),
        OpposingParty(party_id=7, fname="Neelam", lname="Joshi", email="neelam.joshi@example.test", address="Koramangala, Bengaluru", sex="F", repeat_party=True),
        OpposingParty(party_id=8, fname="Harish", lname="Pai", email="harish.pai@example.test", address="Jayanagar, Bengaluru", sex="M", repeat_party=False),
    ]
    db.add_all(groups + pincodes + locations + courts + lawyers + clients + parties)
    db.flush()

    matters = [
        (1, "Recovery of possession, Jayanagar house", "Client seeks possession of a house occupied by a relative after a failed family arrangement.", "OS 112/2024", date(2024, 1, 18), date(2024, 2, 2), "Disposed", 1, 2),
        (2, "Complaint under NI Act for dishonoured cheque", "A cheque issued towards goods supplied at MG Road was returned unpaid.", "CC 448/2024", date(2024, 5, 12), date(2024, 6, 3), "Hearing", 2, 1),
        (3, "Maintenance under personal law", "Petition for monthly maintenance after the respondent left the Hebbal household.", "MC 77/2025", date(2024, 11, 20), date(2025, 1, 9), "Pending", 1, 5),
        (4, "Oppression and mismanagement petition", "Minority shareholder alleges exclusion from management of the Whitefield unit.", "CP 19/2024", date(2024, 3, 2), date(2024, 3, 28), "Disposed", 4, 3),
        (5, "Defence in a hurt prosecution", "Client is accused of causing hurt during a dispute at an Indiranagar shop.", "CC 902/2025", date(2025, 2, 14), date(2025, 3, 1), "Hearing", 2, 4),
        (6, "Damages for delayed industrial supply", "Buyer claims damages for late delivery and a consequent line stoppage.", "OS 640/2025", date(2025, 4, 8), date(2025, 5, 2), "Filed", 1, 6),
        (7, "Divorce and return of stridhan", "Petition for dissolution and return of articles listed in the schedule.", "MC 210/2025", date(2025, 6, 1), date(2025, 6, 19), "Hearing", 1, 4),
        (8, "Temporary injunction against alienation", "Application to restrain sale of the Jayanagar property while title is in dispute.", "OS 113/2024", date(2024, 2, 10), date(2024, 2, 16), "Disposed", 1, 2),
        (9, "Second NI Act complaint, same drawer", "A later cheque from the same retail account was also dishonoured.", "CC 771/2025", date(2025, 8, 22), date(2025, 9, 10), "Filed", 2, 1),
        (10, "Appeal against acquittal", "Appeal challenging an acquittal in a hurt case tried by the magistrate.", "CRL.A 55/2026", date(2025, 1, 30), date(2026, 1, 20), "Hearing", 3, 4),
        (11, "Custody of minor child", "Custody sought for a child residing with the respondent in Hebbal.", "G&W 14/2026", date(2025, 12, 2), date(2026, 1, 8), "Pending", 1, 5),
        (12, "Recovery before the tribunal", "Lender seeks recovery of a term loan secured against the Whitefield plant.", "OA 88/2026", date(2026, 2, 11), date(2026, 3, 4), "Filed", 4, 3),
    ]
    for row in matters:
        db.add(LegalCase(
            case_id=row[0], matter_title=row[1], matter_description=row[2], case_number=row[3],
            date_cause=row[4], date_filed=row[5], status=row[6], court_id=row[7], location_id=row[8],
        ))
    db.flush()

    for case_id, matter_type in [
        (1, "Civil"), (2, "Criminal"), (3, "Family"), (4, "Corporate"),
        (5, "Criminal"), (6, "Civil"), (7, "Family"), (8, "Civil"),
        (9, "Criminal"), (10, "Criminal"), (11, "Family"), (12, "Corporate"),
    ]:
        db.add(MatterType(case_id=case_id, matter_type=matter_type))

    for case_id, section in [
        (1, "Specific Relief Act 5"), (1, "CPC Order VII"), (2, "NI Act 138"),
        (3, "Hindu Adoptions and Maintenance Act 18"), (4, "Companies Act 241"),
        (5, "BNS 115"), (6, "Contract Act 73"), (7, "Hindu Marriage Act 13"),
        (8, "CPC Order XXXIX"), (9, "NI Act 138"), (10, "BNSS 419"),
        (11, "Hindu Minority and Guardianship Act 6"), (12, "RDDBFI Act 19"),
    ]:
        db.add(StatuteSection(case_id=case_id, statute_section=section))

    for case_id, client_id in [(1, 1), (2, 2), (3, 3), (4, 8), (5, 5), (6, 7), (7, 6), (8, 1), (9, 2), (10, 5), (11, 3), (12, 4)]:
        db.add(CaseClient(case_id=case_id, client_id=client_id))
    for case_id, party_id in [(1, 1), (2, 2), (3, 3), (4, 7), (5, 4), (6, 6), (7, 5), (8, 8), (9, 2), (10, 4), (11, 3), (12, 7)]:
        db.add(CaseOpposingParty(case_id=case_id, party_id=party_id))

    for case_id, lawyer_id, role, assigned, ended in [
        (1, 3, "Lead Counsel", date(2024, 2, 2), None),
        (1, 4, "Associate", date(2024, 2, 2), None),
        (2, 1, "Lead Counsel", date(2024, 6, 3), None),
        (2, 2, "Associate", date(2024, 6, 10), None),
        (3, 5, "Lead Counsel", date(2025, 1, 9), None),
        (4, 3, "Lead Counsel", date(2024, 3, 28), date(2024, 11, 1)),
        (4, 6, "Associate", date(2024, 3, 28), None),
        (5, 1, "Lead Counsel", date(2025, 3, 1), None),
        (5, 2, "Research", date(2025, 3, 5), date(2025, 6, 1)),
        (6, 3, "Lead Counsel", date(2025, 5, 2), None),
        (6, 4, "Associate", date(2025, 5, 2), None),
        (7, 5, "Lead Counsel", date(2025, 6, 19), None),
        (8, 4, "Lead Counsel", date(2024, 2, 16), None),
        (9, 2, "Lead Counsel", date(2025, 9, 10), None),
        (9, 1, "Associate", date(2025, 9, 12), None),
        (10, 1, "Lead Counsel", date(2026, 1, 20), None),
        (10, 2, "Associate", date(2026, 1, 20), None),
        (11, 5, "Lead Counsel", date(2026, 1, 8), None),
        (12, 6, "Lead Counsel", date(2026, 3, 4), None),
        (12, 3, "Associate", date(2026, 3, 4), None),
    ]:
        db.add(CaseLawyer(case_id=case_id, lawyer_id=lawyer_id, role=role, assigned_date=assigned, end_date=ended))

    for description, filed, evidence_status, lawyer_id, case_id in [
        ("Certified copy of the title deed and tax receipts", date(2024, 2, 20), "Produced", 3, 1),
        ("Bank return memo and statutory notice", date(2024, 6, 18), "Filed", 1, 2),
        ("Affidavit of assets and liabilities", date(2025, 2, 2), "Under Review", 5, 3),
        ("Board minutes and bank statements", date(2024, 4, 15), "Produced", 6, 4),
        ("Wound certificate with defence notes", date(2025, 4, 2), "Received", 2, 5),
        ("Purchase order and delivery challans", date(2025, 5, 20), "Received", 4, 6),
        ("Schedule of stridhan", date(2025, 7, 1), "Filed", 5, 7),
        ("Affidavit for temporary injunction", date(2024, 2, 16), "Produced", 4, 8),
        ("Second statutory notice", date(2025, 9, 25), "Received", 2, 9),
        ("Certified copy of the magistrate judgment", date(2026, 2, 11), "Filed", 1, 10),
        ("School records and residence affidavit", date(2026, 2, 18), "Under Review", 5, 11),
        ("Loan agreement and statement of account", date(2026, 3, 20), "Received", 6, 12),
    ]:
        db.add(Evidence(description=description, filed_date=filed, status=evidence_status, lawyer_id=lawyer_id, case_id=case_id))

    for case_id, old, new, changed in [
        (1, "Filed", "Hearing", datetime(2024, 4, 12)),
        (1, "Hearing", "Disposed", datetime(2024, 9, 30)),
        (2, "Filed", "Hearing", datetime(2024, 7, 1)),
        (4, "Filed", "Hearing", datetime(2024, 5, 10)),
        (4, "Hearing", "Disposed", datetime(2024, 11, 1)),
        (8, "Filed", "Disposed", datetime(2024, 6, 14)),
    ]:
        db.add(CaseStatusAudit(case_id=case_id, old_status=old, new_status=new, changed_at=changed, changed_by="seed"))

    db.add_all([
        ClientPhoneNo(client_id=1, phoneno="9845111001"),
        ClientPhoneNo(client_id=2, phoneno="9845111002"),
        OpposingPartyPhoneNo(party_id=1, phoneno="9845222001"),
    ])

    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(username="admin", email="admin@example.com", hashed_password=get_password_hash("admin123"), full_name="System Administrator", role="admin", is_active=True))
    if not db.query(User).filter(User.username == "lawyer1").first():
        db.add(User(username="lawyer1", email="lawyer1@example.com", hashed_password=get_password_hash("lawyer123"), full_name="Ananya Rao", role="lawyer", is_active=True))
    if not db.query(User).filter(User.username == "staff1").first():
        db.add(User(username="staff1", email="staff1@example.com", hashed_password=get_password_hash("staff123"), full_name="Records Clerk", role="staff", is_active=True))

    if db.bind.dialect.name == "postgresql":
        for table, column in (
            ("practice_group", "group_id"),
            ("location", "location_id"),
            ("court", "court_id"),
            ("lawyer", "lawyer_id"),
            ("client", "client_id"),
            ("opposing_party", "party_id"),
            ("legal_case", "case_id"),
        ):
            db.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{column}'), "
                f"(SELECT MAX({column}) FROM {table}))"
            ))

    db.commit()
