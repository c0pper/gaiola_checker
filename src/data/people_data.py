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

all_people = [ #  1993-09-04
    Person(name="Simone", surname="Marotta", sex="M", bday="1993-09-04", cf="MRTSMN93P04B905N"),
    Person(name="Smeralda", surname="Brigandi", sex="F", bday="1992-11-21", cf="BRGSRL92S61B905P"),
    Person(name="Carmen", surname="Di Carlo", sex="F", bday="1997-07-09", cf="DCRCMN97L49B905M"),
    Person(name="Federica", surname="Antignano", sex="F", bday="1993-02-11", cf="NTGFRC93B51B905D"),
    Person(name="Carolina", surname="Carotenuto", sex="F", bday="1994-10-24", cf="CRTCLN94R64B905I"),
    Person(name="Giuseppe", surname="Perrotta", sex="M", bday="1991-07-08", cf="PRRGPP91M07B905O"),
    # Please provide the birth date for Manuela Marotta to complete her entry.
    # Person(name="Manuela", surname="Marotta", sex="F", bday="DD-MM-YYYY", cf="MTTMNL93D62F839C"),
]