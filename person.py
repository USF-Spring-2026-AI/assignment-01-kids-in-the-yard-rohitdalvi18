class Person:
    def __init__(self, person_id, year_born, year_died, gender, first_name, last_name):
        self.person_id = person_id
        self.year_born = year_born
        self.year_died = year_died
        self.gender = gender          
        self.first_name = first_name
        self.last_name = last_name

        # relationship info
        self.partner_id = None
        self.children_ids = []

        # True if this person is a descendant of the original 2 founders
        self.is_direct_descendant = False

        # used to avoid generating children twice for the same couple
        self.has_generated_children = False

    def full_name(self):
        return self.first_name + " " + self.last_name

    def add_child(self, child_id):
        self.children_ids.append(child_id)

    def set_partner(self, partner_id):
        self.partner_id = partner_id
