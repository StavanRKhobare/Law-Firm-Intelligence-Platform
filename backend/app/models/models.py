"""
SQLAlchemy models for the law-firm case management database.

The database represents one litigation firm. Practice groups are teams inside
that firm. Courts are the forums currently hearing a matter. Locations are the
places connected to the dispute, normalised through pincode_area.
"""
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    ForeignKey, CheckConstraint,
)
from sqlalchemy.orm import relationship
from ..database import Base


class PracticeGroup(Base):
    __tablename__ = "practice_group"

    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(100), nullable=False)
    description = Column(Text)
    email = Column(String(100), unique=True)
    contactno = Column(String(15))

    lawyers = relationship("Lawyer", back_populates="practice_group")


class PincodeArea(Base):
    __tablename__ = "pincode_area"

    pincode = Column(String(10), primary_key=True)
    city = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)

    locations = relationship("Location", back_populates="pincode_area")
    courts = relationship("Court", back_populates="pincode_area")


class Location(Base):
    __tablename__ = "location"

    location_id = Column(Integer, primary_key=True, autoincrement=True)
    landmark = Column(String(200))
    streetno = Column(String(50))
    pincode = Column(String(10), ForeignKey("pincode_area.pincode", ondelete="SET NULL", onupdate="CASCADE"))

    pincode_area = relationship("PincodeArea", back_populates="locations")
    legal_cases = relationship("LegalCase", back_populates="location")


class Court(Base):
    __tablename__ = "court"

    court_id = Column(Integer, primary_key=True, autoincrement=True)
    court_name = Column(String(200), nullable=False)
    court_type = Column(String(50), nullable=False)
    pincode = Column(String(10), ForeignKey("pincode_area.pincode", ondelete="SET NULL", onupdate="CASCADE"))

    pincode_area = relationship("PincodeArea", back_populates="courts")
    legal_cases = relationship("LegalCase", back_populates="court")


class Lawyer(Base):
    __tablename__ = "lawyer"

    lawyer_id = Column(Integer, primary_key=True, autoincrement=True)
    fname = Column(String(50), nullable=False)
    lname = Column(String(50), nullable=False)
    designation = Column(String(50))
    phoneno = Column(String(15))
    bar_id = Column(String(50), unique=True)
    group_id = Column(Integer, ForeignKey("practice_group.group_id", ondelete="SET NULL", onupdate="CASCADE"))

    practice_group = relationship("PracticeGroup", back_populates="lawyers")
    assignments = relationship("CaseLawyer", back_populates="lawyer", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="lawyer")


class Client(Base):
    __tablename__ = "client"

    client_id = Column(Integer, primary_key=True, autoincrement=True)
    fname = Column(String(50), nullable=False)
    lname = Column(String(50), nullable=False)
    email = Column(String(100))
    address = Column(Text)
    sex = Column(String(1))
    notes = Column(Text)

    __table_args__ = (
        CheckConstraint("sex IN ('M', 'F', 'O')", name="client_sex_check"),
    )

    phone_numbers = relationship("ClientPhoneNo", back_populates="client", cascade="all, delete-orphan")
    cases = relationship("LegalCase", secondary="case_client", back_populates="clients")


class OpposingParty(Base):
    __tablename__ = "opposing_party"

    party_id = Column(Integer, primary_key=True, autoincrement=True)
    fname = Column(String(50), nullable=False)
    lname = Column(String(50), nullable=False)
    email = Column(String(100))
    address = Column(Text)
    sex = Column(String(1))
    repeat_party = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("sex IN ('M', 'F', 'O')", name="opposing_party_sex_check"),
    )

    phone_numbers = relationship("OpposingPartyPhoneNo", back_populates="party", cascade="all, delete-orphan")
    cases = relationship("LegalCase", secondary="case_opposing_party", back_populates="opposing_parties")


class LegalCase(Base):
    __tablename__ = "legal_case"

    case_id = Column(Integer, primary_key=True, autoincrement=True)
    matter_title = Column(String(200), nullable=False)
    matter_description = Column(Text)
    case_number = Column(String(50), unique=True, nullable=False)
    date_cause = Column(Date, nullable=False)
    date_filed = Column(Date, nullable=False)
    status = Column(String(50), default="Filed")
    court_id = Column(Integer, ForeignKey("court.court_id", ondelete="SET NULL", onupdate="CASCADE"))
    location_id = Column(Integer, ForeignKey("location.location_id", ondelete="SET NULL", onupdate="CASCADE"))

    __table_args__ = (
        CheckConstraint("date_filed >= date_cause", name="legal_case_date_check"),
        CheckConstraint(
            "status IN ('Filed', 'Hearing', 'Pending', 'Disposed')",
            name="legal_case_status_check",
        ),
    )

    court = relationship("Court", back_populates="legal_cases")
    location = relationship("Location", back_populates="legal_cases")
    assignments = relationship("CaseLawyer", back_populates="legal_case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="legal_case", cascade="all, delete-orphan")
    matter_types = relationship("MatterType", back_populates="legal_case", cascade="all, delete-orphan")
    statute_sections = relationship("StatuteSection", back_populates="legal_case", cascade="all, delete-orphan")
    clients = relationship("Client", secondary="case_client", back_populates="cases")
    opposing_parties = relationship("OpposingParty", secondary="case_opposing_party", back_populates="cases")
    status_history = relationship("CaseStatusAudit", back_populates="legal_case", cascade="all, delete-orphan")


class CaseLawyer(Base):
    """Counsel assignment. PostgreSQL also has partial unique index one_active_lead_per_case."""

    __tablename__ = "case_lawyer"

    case_id = Column(Integer, ForeignKey("legal_case.case_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    lawyer_id = Column(Integer, ForeignKey("lawyer.lawyer_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False)
    assigned_date = Column(Date, nullable=False)
    end_date = Column(Date)

    __table_args__ = (
        CheckConstraint(
            "role IN ('Lead Counsel', 'Associate', 'Research')",
            name="case_lawyer_role_check",
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= assigned_date",
            name="case_lawyer_date_check",
        ),
    )

    legal_case = relationship("LegalCase", back_populates="assignments")
    lawyer = relationship("Lawyer", back_populates="assignments")


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text)
    filed_date = Column(Date, nullable=False)
    mongo_id = Column(String(100))
    status = Column(String(50), default="Received")
    lawyer_id = Column(Integer, ForeignKey("lawyer.lawyer_id", ondelete="SET NULL", onupdate="CASCADE"))
    case_id = Column(Integer, ForeignKey("legal_case.case_id", ondelete="CASCADE", onupdate="CASCADE"))

    __table_args__ = (
        CheckConstraint(
            "status IN ('Received', 'Under Review', 'Filed', 'Produced')",
            name="evidence_status_check",
        ),
    )

    lawyer = relationship("Lawyer", back_populates="evidence")
    legal_case = relationship("LegalCase", back_populates="evidence")


class CaseClient(Base):
    __tablename__ = "case_client"

    case_id = Column(Integer, ForeignKey("legal_case.case_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    client_id = Column(Integer, ForeignKey("client.client_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)


class CaseOpposingParty(Base):
    __tablename__ = "case_opposing_party"

    case_id = Column(Integer, ForeignKey("legal_case.case_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    party_id = Column(Integer, ForeignKey("opposing_party.party_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)


class ClientPhoneNo(Base):
    __tablename__ = "client_phone_no"

    client_id = Column(Integer, ForeignKey("client.client_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    phoneno = Column(String(15), primary_key=True)

    client = relationship("Client", back_populates="phone_numbers")


class OpposingPartyPhoneNo(Base):
    __tablename__ = "opposing_party_phone_no"

    party_id = Column(Integer, ForeignKey("opposing_party.party_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    phoneno = Column(String(15), primary_key=True)

    party = relationship("OpposingParty", back_populates="phone_numbers")


class MatterType(Base):
    __tablename__ = "matter_type"

    case_id = Column(Integer, ForeignKey("legal_case.case_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    matter_type = Column(String(100), primary_key=True)

    legal_case = relationship("LegalCase", back_populates="matter_types")


class StatuteSection(Base):
    __tablename__ = "statute_section"

    case_id = Column(Integer, ForeignKey("legal_case.case_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    statute_section = Column(String(50), primary_key=True)

    legal_case = relationship("LegalCase", back_populates="statute_sections")


class CaseStatusAudit(Base):
    __tablename__ = "case_status_audit"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("legal_case.case_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    old_status = Column(String(50))
    new_status = Column(String(50))
    changed_at = Column(DateTime)
    changed_by = Column(String(100))

    legal_case = relationship("LegalCase", back_populates="status_history")
