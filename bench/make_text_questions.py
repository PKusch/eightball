"""Builds bench/text_questions.jsonl, the test set for the eight ball's "text mode".

The ball gets a short text and a yes/no question about it. The right answer is:
  yes    the text says so
  no     the text says the opposite
  maybe  the text never says

Every right answer comes from how the item is built, never from a language model.
Each text is written from a small table of facts (a deposit, a due date, whether pets are
allowed). Each question is about ONE attribute of that table:
  yes    the question states the value the table holds
  no     the question states a different, near-miss value (or the opposite policy)
  maybe  the attribute was left out of the table, so the text never mentions it

Yes, no and maybe use the same question shapes, so the wording gives nothing away.
Run:  python bench/make_text_questions.py

Same seed, same file, every time.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

SEED = 8
HERE = Path(__file__).resolve().parent
OUT = HERE / "text_questions.jsonl"
PER_LABEL = 25          # items per kind and label: 8 kinds x 3 labels x 25 = 600
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
CURRENCIES = ["euros", "pounds", "dollars"]
FIELDS = ["id", "text", "question", "label", "kind", "split", "facts", "ask"]

FIRST = ["Priya", "Tomas", "Amara", "Jonas", "Lucia", "Kwame", "Elena", "Marcus", "Sofia", "Dmitri", "Hannah", "Ravi"]
LAST = ["Nair", "Keller", "Okoye", "Lindgren", "Moretti", "Tanaka", "Brandt", "Silva", "Novak", "Haddad", "Osei", "Fischer"]
MONTH_RX = r"\b\d{1,2} (?:%s) \d{4}\b" % "|".join(m.lower() for m in MONTHS)   # a full date such as 4 may 2027


# ----------------------------------------------------------------------------------- attribute spec
class Attr:
    """One thing a text can say. `spec` says how values are drawn; `t` are the sentences that state it
    (a list, or {True: [...], False: [...]} for yes/no policies); `q` are the question shapes in the
    same layout. `probe` is a regex of words that must not appear in a text that leaves the attribute out."""

    def __init__(self, key, spec, t, q, probe):
        self.key, self.spec, self.t, self.q, self.probe = key, spec, t, q, probe
        self.is_bool = spec[0] == "bool"


def A(key, spec, t, q, probe):
    return Attr(key, spec, t, q, probe)


CITY_A = ["Rotterdam", "Antwerp", "Leeds", "Gdansk", "Porto", "Lyon", "Bremen", "Malmo"]
CITY_B = ["Utrecht", "Manchester", "Lyon", "Gothenburg", "Dublin", "Hamburg", "Krakow", "Valencia"]
TOWN = ["Leeds", "Bristol", "Cardiff", "Exeter", "Derby", "Norwich", "Preston", "Hull"]
DAYS = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays"]
DOCTORS = ["Dr Adeyemi", "Dr Lindqvist", "Dr Moreau", "Dr Castillo", "Dr Novak", "Dr Haddad", "Dr Ivanova", "Dr Okafor"]
TEACHERS = ["Professor Weber", "Professor Alvarez", "Dr Kowalski", "Professor Tanaka", "Dr Osei", "Professor Lindgren",
            "Dr Fischer", "Dr Baptiste"]

ATTRS: dict[str, list[Attr]] = {}

ATTRS["invoice"] = [
    A("total", ("money", 80, 4800, 5),
      ["The total due is {v}.", "The amount you owe is {v}.", "Please pay {v} in total."],
      ["Is the total due {v}?", "Is the amount owed {v}?", "Does the invoice come to {v} in total?"],
      r"\btotal\b|\bowe|\bamount\b|\bbalance\b|please pay"),
    A("due_date", ("date",),
      ["Payment is due on {v}.", "The payment deadline is {v}.", "Please settle the invoice by {v}."],
      ["Is payment due on {v}?", "Is the payment deadline {v}?", "Must the invoice be settled by {v}?"],
      rf"deadline|payment is due|settle|due date|{MONTH_RX}"),
    A("late_fee", ("bool",),
      {True: ["A late fee is charged for overdue payments.", "Overdue payments carry a late fee."],
       False: ["No late fee is charged for overdue payments.", "Overdue payments do not carry a late fee."]},
      {True: ["Is there a late fee for overdue payments?", "Are overdue payments charged a late fee?"],
       False: ["Are overdue payments free of any late fee?", "Can the invoice be paid late without a late fee?"]},
      r"late fee|overdue|penalt"),
    A("method", ("choice", ["bank transfer", "credit card", "cheque", "cash", "direct debit"]),
      ["The invoice must be paid by {v}.", "We only accept payment by {v}."],
      ["Must the invoice be paid by {v}?", "Is {v} the accepted payment method?"],
      r"paid by|accept|payment method|bank transfer|credit card|cheque|cash|direct debit"),
    A("number", ("code", "INV-", 5),
      ["The invoice number is {v}.", "This is invoice {v}."],
      ["Is the invoice number {v}?", "Is this invoice {v}?"],
      r"invoice number|invoice no|inv-|this is invoice"),
    A("vat", ("bool",),
      {True: ["The prices on this invoice include VAT.", "VAT is already included in the listed prices."],
       False: ["The prices on this invoice do not include VAT.", "VAT is not included in the listed prices."]},
      {True: ["Do the listed prices include VAT?", "Is VAT already included in the prices?"],
       False: ["Are the listed prices without VAT?", "Is VAT left out of the listed prices?"]},
      r"\bvat\b|\btax"),
    A("hours", ("num", 4, 60, 1),
      ["The invoice covers {v} hours of consulting work.", "You are billed for {v} hours of consulting."],
      ["Does the invoice cover {v} hours of consulting?", "Are {v} hours of consulting billed?"],
      r"hours?|consult|billed for"),
    A("city", ("choice", CITY_A),
      ["This invoice was issued from our {v} office.", "Our {v} office sent you this invoice."],
      ["Was the invoice issued by the {v} office?", "Did the {v} office send the invoice?"],
      r"office|issued"),
]

ATTRS["meeting"] = [
    A("date", ("date",),
      ["The meeting will take place on {v}.", "We are meeting on {v}.", "Please save the date: {v}."],
      ["Is the meeting on {v}?", "Will the meeting take place on {v}?"],
      rf"take place|save the date|meeting on\b|{MONTH_RX}"),
    A("start", ("time", 540, 990, 15),
      ["The meeting starts at {v}.", "We will begin at {v}.", "Kick-off is at {v}."],
      ["Does the meeting start at {v}?", "Is the start time {v}?", "Will we begin at {v}?"],
      r"start|begin|kick-off|\d{1,2}:\d\d"),
    A("room", ("choice", ["the Cedar Room", "the Maple Room", "the Atrium", "Room 4B", "Room 2A",
                          "the Lakeside Room", "the Library", "Studio 3"]),
      ["The meeting will be held in {v}.", "We have booked only {v}.", "You will find us in {v}."],
      ["Will the meeting be held in {v}?", "Is the meeting in {v}?", "Have we booked {v}?"],
      r"held in|booked|find us|\broom\b|studio|atrium|library"),
    A("duration", ("num", 20, 120, 5),
      ["The meeting should last {v} minutes.", "Plan for {v} minutes in total."],
      ["Should the meeting last {v} minutes?", "Will the meeting run for {v} minutes?"],
      r"\blast|minutes|duration|run for|plan for"),
    A("remote", ("bool",),
      {True: ["Colleagues can join remotely by video call.", "A video link is provided for remote attendees."],
       False: ["Nobody can join remotely, as this is an in-person meeting only.",
               "There is no video link, so everyone attends in person."]},
      {True: ["Can people join the meeting remotely?", "Is there a video link for remote attendees?"],
       False: ["Is the meeting in-person only?", "Is remote attendance ruled out?"]},
      r"remote|video|in person|in-person"),
    A("lunch", ("bool",),
      {True: ["Lunch will be provided.", "Lunch will be supplied for everyone."],
       False: ["Lunch will not be provided.", "Lunch will not be supplied."]},
      {True: ["Will lunch be provided?", "Will lunch be supplied for everyone?"],
       False: ["Is lunch excluded from what is supplied?", "Is the meeting without any provided lunch?"]},
      r"lunch|meal|food|catering"),
    A("invited", ("num", 6, 40, 1),
      ["{v} people have been invited.", "The invitation went to {v} people."],
      ["Have {v} people been invited?", "Did the invitation go to {v} people?"],
      r"invited|invitation|guest list"),
    A("organiser", ("person",),
      ["{v} is the sole organiser of the meeting.", "The meeting is organised solely by {v}."],
      ["Is {v} organising the meeting?", "Is the meeting organised by {v}?"],
      r"organis"),
    A("agenda", ("bool",),
      {True: ["The agenda is attached to this email.", "You will find the agenda attached."],
       False: ["The agenda is not attached to this email.", "There is no agenda attached to this email."]},
      {True: ["Is the agenda attached to this email?", "Has the agenda been attached?"],
       False: ["Is the agenda missing from this email?", "Is this email sent without an agenda attached?"]},
      r"agenda"),
]

ATTRS["rental"] = [
    A("rent", ("money", 450, 2400, 10),
      ["The rent is {v} a month.", "Monthly rent is {v}."],
      ["Is the monthly rent {v}?", "Does the flat rent for {v} a month?"],
      r"\brent\b|monthly"),
    A("deposit", ("money", 300, 3000, 50),
      ["A deposit of {v} is required.", "The deposit is {v}."],
      ["Is the deposit {v}?", "Does the deposit come to {v}?"],
      r"deposit"),
    A("bedrooms", ("num", 2, 5, 1),
      ["The flat has {v} bedrooms.", "There are {v} bedrooms."],
      ["Does the flat have {v} bedrooms?", "Are there {v} bedrooms?"],
      r"bedroom"),
    A("pets", ("bool",),
      {True: ["Pets are welcome.", "Tenants may keep pets."],
       False: ["No pets are allowed.", "Tenants may not keep pets."]},
      {True: ["Are pets allowed?", "May tenants keep pets?"],
       False: ["Are pets banned?", "Is keeping pets forbidden?"]},
      r"\bpets?\b|animal|\bdogs?\b|\bcats?\b"),
    A("furnished", ("bool",),
      {True: ["The flat is fully furnished.", "The flat comes with furniture included."],
       False: ["The flat is unfurnished.", "The flat comes without any furniture."]},
      {True: ["Is the flat furnished?", "Does the flat come with furniture?"],
       False: ["Is the flat unfurnished?", "Does the flat come without furniture?"]},
      r"furnish|furniture"),
    A("floor", ("num", 1, 8, 1),
      ["The flat is on floor {v}.", "You will find it on floor {v}."],
      ["Is the flat on floor {v}?", "Is it on floor {v}?"],
      r"floor|storey"),
    A("available", ("date",),
      ["The flat is available from {v}.", "You can move in on {v}."],
      ["Is the flat available from {v}?", "Can a tenant move in on {v}?"],
      rf"available|move in|{MONTH_RX}"),
    A("smoking", ("bool",),
      {True: ["Smoking is allowed inside the flat.", "Tenants may smoke inside the flat."],
       False: ["Smoking is not allowed inside the flat.", "Tenants may not smoke inside the flat."]},
      {True: ["Is smoking allowed inside the flat?", "May tenants smoke in the flat?"],
       False: ["Is smoking banned inside the flat?", "Is smoking forbidden in the flat?"]},
      r"smok"),
    A("heating", ("choice", ["gas", "electricity", "oil", "district heating", "a heat pump", "wood pellets"]),
      ["The heating runs on {v} only.", "The flat is heated with {v} only."],
      ["Does the heating run on {v}?", "Is the flat heated with {v}?"],
      r"heat"),
]

ATTRS["product"] = [
    A("weight", ("num", 100, 900, 10),
      ["The {p} weighs {v} grams.", "Each {p} weighs {v} grams."],
      ["Does the {p} weigh {v} grams?", "Is the weight of the {p} {v} grams?"],
      r"weigh|weight|grams"),
    A("battery", ("num", 6, 48, 2),
      ["The {p} runs for {v} hours on a full charge.", "Battery life of the {p} is {v} hours."],
      ["Does the {p} run for {v} hours on a full charge?", "Is the battery life of the {p} {v} hours?"],
      r"battery|full charge|runs for|hours"),
    A("waterproof", ("bool",),
      {True: ["The {p} is waterproof.", "The {p} has a waterproof casing."],
       False: ["The {p} is not waterproof.", "The {p} does not have a waterproof casing."]},
      {True: ["Is the {p} waterproof?", "Does the {p} have a waterproof casing?"],
       False: ["Is the {p} non-waterproof?", "Does the {p} lack a waterproof casing?"]},
      r"waterproof|water"),
    A("colour", ("choice", ["black", "white", "red", "green", "blue", "orange", "grey"]),
      ["The {p} comes in {v} only.", "The only colour of the {p} is {v}."],
      ["Does the {p} come in {v}?", "Is the colour of the {p} {v}?"],
      r"colou?r|comes in"),
    A("warranty", ("num", 2, 5, 1),
      ["The {p} comes with a {v}-year warranty.", "A {v}-year warranty covers the {p}."],
      ["Does the {p} come with a {v}-year warranty?", "Is the {p} covered by a {v}-year warranty?"],
      r"warrant|guarantee"),
    A("price", ("money", 15, 250, 5),
      ["The {p} costs {v}.", "The {p} is priced at {v}."],
      ["Does the {p} cost {v}?", "Is the {p} priced at {v}?"],
      r"cost|price"),
    A("port", ("choice", ["USB-C port", "micro-USB port", "magnetic dock", "barrel plug"]),
      ["The {p} charges through a {v} only.", "The {p} is charged via a {v} only."],
      ["Does the {p} charge through a {v}?", "Is the {p} charged via a {v}?"],
      r"charges through|is charged|charging|usb|dock|barrel"),
    A("case", ("bool",),
      {True: ["A carrying case is included with the {p}.", "The {p} ships with a carrying case."],
       False: ["No carrying case is included with the {p}.", "The {p} ships without a carrying case."]},
      {True: ["Is a carrying case included with the {p}?", "Does the {p} ship with a carrying case?"],
       False: ["Is a carrying case left out of the {p} package?", "Does the {p} ship without a carrying case?"]},
      r"carrying case|\bcase\b"),
]

ATTRS["delivery"] = [
    A("date", ("date",),
      ["Your parcel will be delivered on {v}.", "Delivery is scheduled for {v}."],
      ["Will the parcel be delivered on {v}?", "Is delivery scheduled for {v}?"],
      rf"delivered on|scheduled for|{MONTH_RX}"),
    A("slot", ("choice", ["the morning", "the afternoon", "the evening"]),
      ["The driver will arrive in {v}.", "Expect the driver in {v}."],
      ["Will the driver arrive in {v}?", "Should you expect the driver in {v}?"],
      r"driver|morning|afternoon|evening|arrive"),
    A("signature", ("bool",),
      {True: ["A signature is required on delivery.", "Someone must sign for the parcel."],
       False: ["No signature is required on delivery.", "Nobody needs to sign for the parcel."]},
      {True: ["Is a signature required on delivery?", "Does someone have to sign for the parcel?"],
       False: ["Can the parcel be received without a signature?", "Is a signature unnecessary on delivery?"]},
      r"sign"),
    A("weight", ("num", 1, 25, 1),
      ["The parcel weighs {v} kg.", "The total weight of the parcel is {v} kg."],
      ["Does the parcel weigh {v} kg?", "Is the weight of the parcel {v} kg?"],
      r"weigh|\bkg\b"),
    A("tracking", ("code", "TR-", 6),
      ["Your tracking code is {v}.", "Track the parcel with code {v}."],
      ["Is the tracking code {v}?", "Can the parcel be tracked with code {v}?"],
      r"track"),
    A("carrier", ("choice", ["Northway", "Bluebird", "Swiftline", "Ridgeway", "Parcelhop", "Greenline"]),
      ["Your parcel is travelling with {v} only.", "{v} alone is delivering your parcel."],
      ["Is {v} carrying the parcel?", "Is {v} the delivery company?"],
      r"travelling with|delivering|delivery company|northway|bluebird|swiftline|ridgeway|parcelhop|greenline"),
    A("fee", ("money", 2, 20, 1),
      ["The delivery fee is {v}.", "Delivery costs {v}."],
      ["Is the delivery fee {v}?", "Does delivery cost {v}?"],
      r"\bfee\b|costs"),
    A("town", ("choice", TOWN),
      ["The parcel is going to {v}.", "The delivery address is in {v}."],
      ["Is the parcel going to {v}?", "Is the delivery address in {v}?"],
      r"going to|address"),
    A("insured", ("bool",),
      {True: ["The parcel is insured against loss.", "The parcel is covered by transit insurance."],
       False: ["The parcel is not insured against loss.", "The parcel is not covered by transit insurance."]},
      {True: ["Is the parcel insured against loss?", "Is the parcel covered by transit insurance?"],
       False: ["Is the parcel uninsured?", "Is the parcel without transit insurance?"]},
      r"insur|covered"),
]

ATTRS["job"] = [
    A("salary", ("money", 28000, 90000, 1000),
      ["The salary is {v} a year.", "The role pays {v} per year."],
      ["Is the salary {v} a year?", "Does the role pay {v} per year?"],
      r"salary|\bpays\b"),
    A("location", ("choice", CITY_B),
      ["The role is based in {v}.", "Our office for this role is in {v}."],
      ["Is the role based in {v}?", "Is the office for this role in {v}?"],
      r"based in|office"),
    A("home", ("bool",),
      {True: ["Employees may work from home.", "Working from home is allowed."],
       False: ["Employees may not work from home.", "Working from home is not allowed."]},
      {True: ["Can employees work from home?", "Is working from home allowed?"],
       False: ["Is working from home banned?", "Is working from home ruled out?"]},
      r"home|remote"),
    A("experience", ("num", 2, 8, 1),
      ["The role requires {v} years of experience.", "Applicants need {v} years of experience."],
      ["Does the role require {v} years of experience?", "Do applicants need {v} years of experience?"],
      r"experience"),
    A("deadline", ("date",),
      ["Applications close on {v}.", "Send your application by {v}."],
      ["Do applications close on {v}?", "Is the application deadline {v}?"],
      rf"applications? close|your application|deadline|{MONTH_RX}"),
    A("contract", ("choice", ["permanent", "fixed-term"]),
      ["The position is offered on a {v} contract.", "This is a {v} contract."],
      ["Is the position offered on a {v} contract?", "Is this a {v} contract?"],
      r"contract|permanent|fixed-term"),
    A("team", ("num", 4, 15, 1),
      ["The new hire will join a team of {v} people.", "You will work in a team of {v} people."],
      ["Will the new hire join a team of {v} people?", "Is the team made up of {v} people?"],
      r"\bteam\b"),
    A("holiday", ("num", 20, 30, 1),
      ["The job comes with {v} days of paid holiday.", "You get {v} days of paid holiday."],
      ["Does the job come with {v} days of paid holiday?", "Do employees get {v} days of paid holiday?"],
      r"holiday|leave|vacation"),
    A("degree", ("bool",),
      {True: ["A university degree is required.", "Applicants must hold a university degree."],
       False: ["A university degree is not required.", "Applicants do not need a university degree."]},
      {True: ["Is a university degree required?", "Must applicants hold a university degree?"],
       False: ["Is a university degree unnecessary?", "Can applicants apply without a university degree?"]},
      r"degree|universit"),
    A("probation", ("num", 2, 6, 1),
      ["The probation period lasts {v} months.", "New hires serve a probation period of {v} months."],
      ["Does the probation period last {v} months?", "Is the probation period {v} months?"],
      r"probation"),
]

ATTRS["clinic"] = [
    A("date", ("date",),
      ["Your appointment is on {v}.", "We have booked you in for {v}."],
      ["Is the appointment on {v}?", "Are you booked in for {v}?"],
      rf"appointment is on|booked you in|{MONTH_RX}"),
    A("time", ("time", 480, 1050, 5),
      ["The appointment is at {v}.", "Your slot starts at {v}."],
      ["Is the appointment at {v}?", "Does the slot start at {v}?"],
      r"\d{1,2}:\d\d|\bslot\b|appointment is at"),
    A("clinician", ("choice", DOCTORS),
      ["You will be seen by {v}.", "{v} will see you."],
      ["Will you be seen by {v}?", "Will {v} see you?"],
      r"seen by|will see you|\bdr "),
    A("fasting", ("bool",),
      {True: ["You need to fast before the appointment.", "Please do not eat before the appointment."],
       False: ["You do not need to fast before the appointment.", "You may eat normally before the appointment."]},
      {True: ["Do you need to fast before the appointment?", "Must you avoid eating before the appointment?"],
       False: ["Can you eat normally before the appointment?", "Is fasting unnecessary before the appointment?"]},
      r"fast|\beat"),
    A("early", ("num", 5, 30, 5),
      ["Please arrive {v} minutes early.", "We ask patients to check in {v} minutes early."],
      ["Are you asked to arrive {v} minutes early?", "Should patients check in {v} minutes early?"],
      r"early|check in|arrive"),
    A("floor", ("num", 1, 6, 1),
      ["The clinic is on floor {v}.", "You will find us on floor {v}."],
      ["Is the clinic on floor {v}?", "Will you find the clinic on floor {v}?"],
      r"floor"),
    A("referral", ("bool",),
      {True: ["Please bring your referral letter.", "You must bring a referral letter with you."],
       False: ["You do not need to bring a referral letter.", "A referral letter is not needed."]},
      {True: ["Do you need to bring a referral letter?", "Must you bring a referral letter?"],
       False: ["Is a referral letter unnecessary?", "Can you attend without a referral letter?"]},
      r"referral"),
    A("fee", ("money", 10, 60, 5),
      ["A fee of {v} is charged for missed appointments.", "Missed appointments carry a fee of {v}."],
      ["Is the fee for a missed appointment {v}?", "Do missed appointments carry a fee of {v}?"],
      r"\bfee\b|missed|missing"),
    A("duration", ("num", 15, 60, 5),
      ["The appointment lasts {v} minutes.", "Please allow {v} minutes for the visit."],
      ["Does the appointment last {v} minutes?", "Should you allow {v} minutes for the visit?"],
      r"\blasts\b|please allow|for the visit"),
    A("parking", ("bool",),
      {True: ["Patient parking is available at the clinic.", "You can park at the clinic."],
       False: ["There is no patient parking at the clinic.", "You cannot park at the clinic."]},
      {True: ["Is patient parking available at the clinic?", "Can you park at the clinic?"],
       False: ["Is patient parking unavailable at the clinic?", "Is parking at the clinic ruled out?"]},
      r"park"),
]

ATTRS["class"] = [
    A("room", ("choice", ["Room 101", "Room 204", "Room 12B", "the Lecture Hall", "the Science Lab", "Hall C",
                          "Room 310", "the Studio"]),
      ["The class meets in {v}.", "Lessons take place in {v}."],
      ["Does the class meet in {v}?", "Do lessons take place in {v}?"],
      r"meets in|take place in|\broom\b|\bhall\b|\blab\b|studio"),
    A("weekday", ("choice", DAYS),
      ["The class meets once a week, on {v}.", "There is one session a week, on {v}."],
      ["Does the class meet on {v}?", "Is the weekly session on {v}?"],
      rf"once a week|one session|weekly|{'|'.join(d.lower() for d in DAYS)}"),
    A("start", ("time", 480, 1170, 15),
      ["Each session starts at {v}.", "Sessions begin at {v}."],
      ["Does each session start at {v}?", "Do sessions begin at {v}?"],
      r"starts at|begin at|\d\d:\d\d"),
    A("exam", ("bool",),
      {True: ["There is a final exam.", "Students sit a final exam at the end of the course."],
       False: ["There is no final exam.", "Students do not sit a final exam."]},
      {True: ["Is there a final exam?", "Do students sit a final exam?"],
       False: ["Is the course without a final exam?", "Is a final exam left out of the course?"]},
      r"exam"),
    A("textbook", ("bool",),
      {True: ["Students need to buy the textbook.", "Buying the textbook is a must for students."],
       False: ["Students do not need to buy the textbook.", "Buying the textbook is optional."]},
      {True: ["Do students need to buy the textbook?", "Must students buy the textbook?"],
       False: ["Is buying the textbook optional?", "Can students skip buying the textbook?"]},
      r"textbook"),
    A("instructor", ("choice", TEACHERS),
      ["The course is taught only by {v}.", "The only instructor of the course is {v}."],
      ["Is the course taught by {v}?", "Does {v} teach the course?"],
      r"taught|teaches|instructor"),
    A("credits", ("num", 3, 12, 1),
      ["The course is worth {v} credits.", "Passing earns {v} credits."],
      ["Is the course worth {v} credits?", "Does passing earn {v} credits?"],
      r"credits"),
    A("capacity", ("num", 12, 40, 2),
      ["The class is limited to {v} students.", "Enrolment is capped at {v} students."],
      ["Is the class limited to {v} students?", "Is enrolment capped at {v} students?"],
      r"limited to|capped|enrol"),
    A("penalty", ("num", 5, 25, 5),
      ["Late homework loses {v} percent of its marks.", "Handing in homework late costs {v} percent of the marks."],
      ["Does late homework lose {v} percent of its marks?", "Does handing in homework late cost {v} percent of the marks?"],
      r"homework|handing in"),
    A("attendance", ("bool",),
      {True: ["Attendance is compulsory.", "Students must attend every session."],
       False: ["Attendance is optional.", "Students are free to skip sessions."]},
      {True: ["Is attendance compulsory?", "Must students attend every session?"],
       False: ["Is attendance optional?", "Can students skip sessions?"]},
      r"attend|skip"),
    A("term", ("date",),
      ["The term starts on {v}.", "Classes begin on {v}."],
      ["Does the term start on {v}?", "Do classes begin on {v}?"],
      rf"\bterm\b|classes begin|{MONTH_RX}"),
]

PRODUCT_NAMES = ["Nova", "Lumen", "Aero", "Tiro", "Brio", "Kesa"]
PRODUCT_NOUNS = ["camping lantern", "handheld fan", "pocket torch", "bike light"]

# Sentences that carry no attribute. They open or close a text and must never hint at any attribute.
FILLERS = {
    "invoice": (["Thank you for your recent order.", "Here is your invoice.", "Please find your invoice below."],
                ["Thank you for your business.", "Please keep this invoice for your records.",
                 "Contact our accounts team if anything looks wrong."]),
    "meeting": (["Hello everyone.", "Hi all, here are the details for our next meeting.",
                 "This is a quick note about the upcoming meeting."],
                ["Please let me know if you have any questions.", "Thanks for your time.",
                 "Have a good week."]),
    "rental": (["Details of a flat to let are below.", "Please read the listing for this flat.",
                "We are advertising a flat."],
               ["Viewings can be arranged on request.", "Get in touch to find out more.",
                "Thank you for your interest."]),
    "product": (["Here are the technical details.", "This sheet lists the main specifications.",
                 "Please read the specifications below."],
                ["Instructions are available on our website.", "Please check the details carefully before ordering.",
                 "Thank you for choosing us."]),
    "delivery": (["This is an automatic message about your order.", "Here is an update on your order.",
                  "Your order is on its way."],
                 ["Thank you for shopping with us.", "Please do not reply to this message.",
                  "We hope you enjoy your purchase."]),
    "job": (["We are hiring for an open position.", "Here is a summary of a job we are advertising.",
             "Please read about our vacancy below."],
            ["We look forward to hearing from you.", "Thank you for your interest.",
             "Feel free to share this posting."]),
    "clinic": (["This is a reminder from your local clinic.", "Hello, this is a message about your booking.",
                "Here is a short reminder."],
               ["Call us if you need to change anything.", "Thank you, and take care.",
                "We look forward to seeing you."]),
    "class": (["Welcome to the course.", "This note explains how the course works.",
               "Here is a short note for new students."],
              ["Please read this note carefully.", "We hope you enjoy the course.",
               "Ask the office if something is unclear."]),
}
PREFIX = {"invoice": "inv", "meeting": "mtg", "rental": "rnt", "product": "prd", "delivery": "dlv",
          "job": "job", "clinic": "cln", "class": "cls"}
KINDS = list(PREFIX)
CTX_KEYS = {"product": ["p"]}   # context values the sentences of a kind refer to (stored with the facts)


def make_ctx(rng: random.Random, kind: str) -> dict:
    if kind == "product":
        return {"p": f"{rng.choice(PRODUCT_NAMES)} {rng.choice([100, 200, 300, 500])} {rng.choice(PRODUCT_NOUNS)}"}
    return {}


# ------------------------------------------------------------------------------------------- values
def fmt_date(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def parse_date(s: str) -> date:
    day, month, year = s.split()
    return date(int(year), MONTHS.index(month) + 1, int(day))


def fmt_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def gen_value(spec, rng: random.Random, cur: str):
    kind = spec[0]
    if kind == "num":
        return rng.randrange(spec[1], spec[2] + 1, spec[3])
    if kind == "money":
        return f"{rng.randrange(spec[1], spec[2] + 1, spec[3])} {cur}"
    if kind == "date":
        return fmt_date(date.fromordinal(rng.randint(date(2027, 1, 4).toordinal(), date(2028, 6, 30).toordinal())))
    if kind == "time":
        return fmt_time(rng.randrange(spec[1], spec[2] + 1, spec[3]))
    if kind == "choice":
        return rng.choice(spec[1])
    if kind == "person":
        return f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    if kind == "code":
        return spec[1] + "".join(str(rng.randrange(10)) for _ in range(spec[2]))
    if kind == "bool":
        return rng.random() < 0.5
    raise ValueError(spec)


def wrong_value(spec, v, rng: random.Random, cur: str):
    """A different value of the same kind that is a near miss, never equal to v."""
    kind = spec[0]
    if kind == "num":
        opts = [v + spec[3] * k for k in (-3, -2, -1, 1, 2, 3)]
        opts = [x for x in opts if spec[1] <= x <= spec[2]]
        return rng.choice(opts)
    if kind == "money":
        n = int(v.split()[0])
        opts = [n + spec[3] * k for k in (-6, -4, -3, -2, -1, 1, 2, 3, 4, 6)]
        opts += [round(n * 1.1 / spec[3]) * spec[3], round(n * 0.9 / spec[3]) * spec[3]]
        opts = [x for x in opts if x > 0 and x != n and spec[1] <= x <= spec[2]]
        return f"{rng.choice(opts)} {cur}"
    if kind == "date":
        return fmt_date(date.fromordinal(parse_date(v).toordinal() + rng.choice([-30, -21, -14, -10, -7, -5, -3, -2, -1, 1, 2, 3, 5, 7, 10, 14, 21, 30])))
    if kind == "time":
        h, m = map(int, v.split(":"))
        opts = [h * 60 + m + k for k in (-120, -90, -60, -45, -30, -15, 15, 30, 45, 60, 90, 120)]
        opts = [x for x in opts if 420 <= x <= 1140]
        return fmt_time(rng.choice(opts))
    if kind == "choice":
        return rng.choice([x for x in spec[1] if x != v])
    if kind == "person":
        first, last = v.split()
        if rng.random() < 0.5:
            return f"{rng.choice([f for f in FIRST if f != first])} {last}"
        return f"{first} {rng.choice([l for l in LAST if l != last])}"
    if kind == "code":
        digits = list(v[len(spec[1]):])
        for i in rng.sample(range(len(digits)), rng.choice([1, 2])):
            digits[i] = rng.choice([d for d in "0123456789" if d != digits[i]])
        w = spec[1] + "".join(digits)
        return w if w != v else wrong_value(spec, v, rng, cur)
    if kind == "bool":
        return not v
    raise ValueError(spec)


def in_range(spec, v) -> bool:
    """Would this value be a natural value for an attribute of this spec?"""
    if spec[0] == "num":
        return isinstance(v, int) and spec[1] <= v <= spec[2] and (v - spec[1]) % spec[3] == 0
    if spec[0] == "money":
        n = int(v.split()[0])
        return spec[1] <= n <= spec[2] and (n - spec[1]) % spec[3] == 0
    return False


# --------------------------------------------------------------------------------------- rendering
def render_sentence(attr: Attr, value, ctx: dict, rng: random.Random) -> str:
    tpl = rng.choice(attr.t[value] if attr.is_bool else attr.t)
    return tpl.format(v=value, **ctx)


def render_question(attr: Attr, value, ctx: dict, rng: random.Random) -> str:
    tpl = rng.choice(attr.q[value] if attr.is_bool else attr.q)
    return tpl.format(v=value, **ctx)


def make_item(rng: random.Random, kind: str, label: str, ask_key: str) -> dict:
    attrs = ATTRS[kind]
    by_key = {a.key: a for a in attrs}
    ask = by_key[ask_key]
    cur = rng.choice(CURRENCIES)
    ctx = make_ctx(rng, kind)
    values = {a.key: gen_value(a.spec, rng, cur) for a in attrs}
    n = rng.randint(3, 5)
    others = [a.key for a in attrs if a.key != ask_key]
    present = rng.sample(others, n) if label == "maybe" else [ask_key] + rng.sample(others, n - 1)
    present.sort(key=lambda k: [a.key for a in attrs].index(k))

    if label == "yes":
        asserted = values[ask_key]
    elif label == "no":
        asserted = wrong_value(ask.spec, values[ask_key], rng, cur)
    else:
        asserted = gen_value(ask.spec, rng, cur)
    # Sometimes the asserted value is one the text states for a different attribute (a trap for
    # word-matching): the number 3 appears in the text, but as the floor, not as the bedrooms.
    if ask.spec[0] in ("num", "money") and rng.random() < 0.4:
        pool = [values[k] for k in present if k != ask_key and by_key[k].spec[0] == ask.spec[0]
                and in_range(ask.spec, values[k]) and (label == "maybe" or values[k] != values[ask_key])]
        if pool and label != "yes":
            asserted = rng.choice(pool)

    sentences = [render_sentence(by_key[k], values[k], ctx, rng) for k in present]
    rng.shuffle(sentences)
    intro, outro = FILLERS[kind]
    nf = rng.choice([0, 1, 1, 2])
    if nf == 2 or (nf == 1 and rng.random() < 0.5):
        sentences.insert(0, rng.choice(intro))
    if nf == 2 or (nf == 1 and sentences[0] not in intro):
        sentences.append(rng.choice(outro))
    facts = dict(ctx)
    facts.update({k: values[k] for k in present})
    return {"text": " ".join(sentences), "question": render_question(ask, asserted, ctx, rng),
            "label": label, "kind": kind, "facts": facts, "ask": {"attr": ask_key, "value": asserted}}


def build_kind(kind: str) -> list[dict]:
    items, seen = [], set()
    keys = [a.key for a in ATTRS[kind]]
    for label in ("yes", "no", "maybe"):
        rng = random.Random(f"{SEED}:{kind}:{label}")
        schedule: list[str] = []
        while len(schedule) < PER_LABEL:          # every attribute is asked about equally often
            perm = keys[:]
            rng.shuffle(perm)
            schedule += perm
        for ask_key in schedule[:PER_LABEL]:
            for _ in range(200):
                it = make_item(rng, kind, label, ask_key)
                if it["text"] not in seen:
                    seen.add(it["text"])
                    items.append(it)
                    break
            else:
                raise AssertionError((kind, label, "cannot make a new text"))
    return items


def build() -> list[dict]:
    """Return every item with id and split, in file order. Deterministic."""
    items: list[dict] = []
    for kind in KINDS:
        items += build_kind(kind)
    rng = random.Random(f"{SEED}:shuffle")
    groups = defaultdict(list)
    for it in items:
        groups[(it["kind"], it["label"])].append(it)
    for key in sorted(groups):                    # stratified: about one third dev, for every kind and label
        g = groups[key]
        rng.shuffle(g)
        n_dev = max(1, round(len(g) / 3))
        for i, it in enumerate(g):
            it["split"] = "dev" if i < n_dev else "test"
    rng.shuffle(items)
    counter = Counter()
    out = []
    for it in items:
        counter[it["kind"]] += 1
        it["id"] = f"{PREFIX[it['kind']]}-{counter[it['kind']]:04d}"
        out.append({f: it[f] for f in FIELDS})
    return out


def main() -> None:
    items = build()
    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    by = Counter((it["kind"], it["label"]) for it in items)
    print(f"wrote {len(items)} items to {OUT}")
    print("labels:", dict(Counter(it["label"] for it in items)))
    print("splits:", dict(Counter(it["split"] for it in items)))
    for kind in KINDS:
        print(f"  {kind:9s} yes={by[(kind, 'yes')]:3d} no={by[(kind, 'no')]:3d} maybe={by[(kind, 'maybe')]:3d}")


if __name__ == "__main__":
    main()
