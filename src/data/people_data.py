# src/data/people_data.py
from dataclasses import dataclass

@dataclass
class Person:
    """
    Dataclass to represent a person's details for booking.
    """
    name: str
    surname: str
    sex: str
    bday: str
    cf: str # Codice Fiscale (Italian Tax Code)

all_people = [
    Person(name="Simone", surname="Marotta", sex="M", bday="04-09-1993", cf="MRTSNM93P04F839B"),
    Person(name="Smeralda", surname="Brigandì", sex="F", bday="21-11-1992", cf="BRGSRL92S61F839C"),
    Person(name="Carmen", surname="Di Carlo", sex="F", bday="09-07-1997", cf="DCRCMN97L49F839Z"),
    Person(name="Federica", surname="Antignano", sex="F", bday="11-02-1993", cf="NTGFRC93B51F839Q"),
    Person(name="Carolina", surname="Carotenuto", sex="F", bday="24-10-1994", cf="CRTCLN94R64F839V"),
    Person(name="Giuseppe", surname="Perrotta", sex="M", bday="07-08-1991", cf="PRRGPP91M07F839B"),
    # Please provide the birth date for Manuela Marotta to complete her entry.
    # Person(name="Manuela", surname="Marotta", sex="F", bday="DD-MM-YYYY", cf="MTTMNL93D62F839C"),
]