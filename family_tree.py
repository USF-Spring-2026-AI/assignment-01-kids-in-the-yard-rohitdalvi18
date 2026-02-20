# Generates the family tree and provides menu queries (T, D, N, Q)

import math

from person_factory import PersonFactory


class FamilyTree:
    def __init__(self, person_factory):
        self.pf = person_factory

        # person_id -> Person object
        self.people = {}

        # store founder IDs and last names
        self.founder1_id = None
        self.founder2_id = None
        self.founder_last_names = None  # tuple ("last_name1", "last_name2")

    # ----------------- storing people -----------------

    def add_person(self, person):
        self.people[person.person_id] = person

    def get_person(self, pid):
        return self.people[pid]

    # ----------------- generation -----------------

    def generate_tree(self):
        """
        Starting with 2 founders born in 1950.
        Then expanding generation by generation (queue) until no children or year > 2120.
        """
        # create founders 
        founder1 = self.pf.create_person(1950, is_direct_descendant=False)
        founder2 = self.pf.create_person(1950, is_direct_descendant=False)

        # set them as partners
        founder1.set_partner(founder2.person_id)
        founder2.set_partner(founder1.person_id)

        # mark them as direct descendant line root (their kids will be descendants)
        # founders themselves aren't descendants, but for simplicity we keep is_direct_descendant False on them

        self.add_person(founder1)
        self.add_person(founder2)

        self.founder1_id = founder1.person_id
        self.founder2_id = founder2.person_id
        self.founder_last_names = (founder1.last_name, founder2.last_name)

        # queue for BFS expansion
        queue = []
        queue.append(founder1.person_id)
        queue.append(founder2.person_id)

        # BFS: each person may create spouse if missing and children
        while len(queue) > 0:
            pid = queue.pop(0)
            person = self.get_person(pid)

            # If this person is already too young (born after 2120), ignore
            if person.year_born > 2120:
                continue

            # create a partner (spouse) if they don't have one
            if person.partner_id is None:
                self.maybe_create_partner(person)

            # create children based on rates
            children = self.create_children_for_person(person)

            # add children to queue for further expansion
            for child in children:
                queue.append(child.person_id)

    def maybe_create_partner(self, person):
        """
        Use decade marriage_rate to decide if this person gets a spouse.
        spouse is NOT a direct descendant so last name is sampled normally.
        spouse year born within +/- 10 years.
        """
        decade = self.pf.year_to_decade(person.year_born)

        # if no rate available, skip
        if decade not in self.pf.rates_by_decade:
            return

        marriage_rate, birth_rate = self.pf.rates_by_decade[decade]

        # roll probability
        roll = self.pf.rng.random()
        if roll > marriage_rate:
            return  # no spouse

        # create spouse
        spouse_year = person.year_born + self.pf.rng.randint(-10, 10)

        # make sure spouse year is reasonable
        if spouse_year < 1900:
            spouse_year = 1900

        spouse = self.pf.create_person(spouse_year, is_direct_descendant=False)

        # connect both ways
        person.set_partner(spouse.person_id)
        spouse.set_partner(person.person_id)

        # store spouse
        self.add_person(spouse)

    def create_children_for_person(self, person):
        decade = self.pf.year_to_decade(person.year_born)

        if decade not in self.pf.rates_by_decade:
            return []

        # Prevent generating children twice
        if person.has_generated_children:
            return []

        birth_rate, marriage_rate = self.pf.rates_by_decade[decade]

        # round up on bounds
        min_kids = int(math.ceil(birth_rate - 1.5))
        max_kids = int(math.ceil(birth_rate + 1.5))

        if min_kids < 0:
            min_kids = 0
        if max_kids < 0:
            max_kids = 0

        if max_kids < min_kids:
            num_children = 0
        else:
            num_children = self.pf.rng.randint(min_kids, max_kids)

        # if no spouse, 1 fewer child
        if person.partner_id is None and num_children > 0:
            num_children -= 1

        if num_children <= 0:
            person.has_generated_children = True
            return []

        elder_year = person.year_born
        partner = None
        if person.partner_id is not None and person.partner_id in self.people:
            partner = self.get_person(person.partner_id)
            if partner.year_born < elder_year:
                elder_year = partner.year_born

            # If partner already generated kids, don't do it again
            if partner.has_generated_children:
                return []

        start_year = elder_year + 25
        end_year = elder_year + 45
        span = end_year - start_year

        children = []
        for i in range(num_children):
            if num_children == 1:
                child_year = start_year
            else:
                child_year = start_year + int(round((span * i) / (num_children - 1)))

            if child_year > 2120:
                continue

            is_desc = False
            if person.person_id == self.founder1_id or person.person_id == self.founder2_id:
                is_desc = True
            if person.is_direct_descendant:
                is_desc = True

            child = self.pf.create_person(
                child_year,
                is_direct_descendant=is_desc,
                allowed_last_names=self.founder_last_names
            )
            child.is_direct_descendant = is_desc

            self.add_person(child)
            person.add_child(child.person_id)

            if partner is not None:
                partner.add_child(child.person_id)

            children.append(child)

        # Mark both as done so we don't generate twice
        person.has_generated_children = True
        if partner is not None:
            partner.has_generated_children = True

        return children


    # ----------------- queries -----------------

    def total_people(self):
        return len(self.people)

    def people_by_decade(self):
        """
        Returns dict: decade -> count
        decade based on year_born.
        """
        counts = {}
        for pid in self.people:
            p = self.people[pid]
            decade = self.pf.year_to_decade(p.year_born)
            if decade not in counts:
                counts[decade] = 0
            counts[decade] += 1
        return counts

    def duplicate_names(self):
        """
        Returns a dict: full_name -> count (only for names that appear more than once)
        """
        name_count = {}

        for pid in self.people:
            p = self.people[pid]
            nm = p.full_name()
            if nm not in name_count:
                name_count[nm] = 0
            name_count[nm] += 1

        dups = {}
        for nm in name_count:
            if name_count[nm] > 1:
                dups[nm] = name_count[nm]

        return dups


    # ----------------- menu / CLI -----------------

    def run_menu(self):
        def print_menu():
            print()
            print("Enter one of the following options:")
            print("T - total number of people")
            print("D - number of people born each decade")
            print("N - number of people with the same name (duplicates)")
            print("Q - quit")

        print("Family tree generated.")
        print_menu()

        while True:
            choice = input("Your choice: ").strip().upper()

            if choice == "T":
                print("Total people:", self.total_people())

            elif choice == "D":
                counts = self.people_by_decade()
                for dec in sorted(counts.keys()):
                    print(dec + ":", counts[dec])

            elif choice == "N":
                dups = self.duplicate_names()
                if len(dups) == 0:
                    print("No duplicate full names found.")
                else:
                    print("Duplicate full names (with counts):")
                    for nm in sorted(dups.keys()):
                        print("- " + nm + " (" + str(dups[nm]) + ")")

            elif choice == "Q":
                print("Bye!")
                break

            else:
                print("Invalid input. Please enter T, D, N, or Q.")

            print_menu()

