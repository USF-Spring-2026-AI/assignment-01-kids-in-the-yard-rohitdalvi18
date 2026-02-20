# This class reads CSV files and provides helper functions to create people

import csv
import random

from person import Person


class PersonFactory:
    def __init__(self, data_dir=".", seed=None):
        self.data_dir = data_dir
        # Reference: Python random module docs (used for rng.random())
        # https://docs.python.org/3/library/random.html#random.random
        self.rng = random.Random(seed)
        self.next_id = 1

        # Loaded data
        self.rates_by_decade = {}          # "1950s" -> (birth_rate, marriage_rate)
        self.first_names = {}              # ("1950s","male") -> [(name, freq), ...]
        self.gender_probs = {}             # "1950s" -> {"male": p, "female": p}
        self.life_exp_by_decade = {}       # "1950s" -> avg life expectancy
        self.max_life_exp_decade = None    # fallback decade for life expectancy
        self.last_names_by_decade = {}     # "1950s" -> [(last, weight), ...]

    # ---------------- helpers ----------------

    def year_to_decade(self, year):
        decade = (year // 10) * 10
        return str(decade) + "s"

    def weighted_pick(self, items):
        """
        items = [(value, weight), ...]
        weights don't need to add up to 1.
        """
        total = 0.0
        for _, w in items:
            total += float(w)

        if total <= 0:
            # fallback: uniform pick
            return items[self.rng.randrange(len(items))][0]

        r = self.rng.random() * total
        upto = 0.0
        for val, w in items:
            upto += float(w)
            if upto >= r:
                return val
        return items[-1][0]  

    # ---------------- main load ----------------

    def read_files(self):
        self._load_birth_and_marriage_rates()
        self._load_first_names()
        self._load_gender_probabilities()
        self._load_life_expectancy()
        self._load_last_names_ranked()

    # ---------------- CSV loaders ----------------

    def _load_birth_and_marriage_rates(self):
        path = self.data_dir + "/birth_and_marriage_rates.csv"
        with open(path, "r", newline="", encoding="utf-8") as f:
            # Reference: csv.DictReader docs
            # https://docs.python.org/3/library/csv.html#csv.DictReader
            reader = csv.DictReader(f)
            for row in reader:
                decade = row["decade"].strip()
                birth_rate = float(row["birth_rate"])
                marriage_rate = float(row["marriage_rate"])
                self.rates_by_decade[decade] = (birth_rate, marriage_rate)

    def _load_first_names(self):
        path = self.data_dir + "/first_names.csv"
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                decade = row["decade"].strip()
                gender = row["gender"].strip().lower()  # "male" / "female"
                name = row["name"].strip()
                freq = float(row["frequency"])

                key = (decade, gender)
                if key not in self.first_names:
                    self.first_names[key] = []
                self.first_names[key].append((name, freq))

    def _load_gender_probabilities(self):
        path = self.data_dir + "/gender_name_probability.csv"
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                decade = row["decade"].strip()
                gender = row["gender"].strip().lower()
                prob = float(row["probability"])

                if decade not in self.gender_probs:
                    self.gender_probs[decade] = {}
                self.gender_probs[decade][gender] = prob

    def _load_life_expectancy(self):
        """
        life_expectancy.csv columns:
          Year, Period life expectancy at birth

        average by decade (1950-1959 -> "1950s", etc.)
        """
        path = self.data_dir + "/life_expectancy.csv"
        buckets = {}  # decade -> [vals]

        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                year = int(row["Year"])
                val = float(row["Period life expectancy at birth"])
                decade = self.year_to_decade(year)

                if decade not in buckets:
                    buckets[decade] = []
                buckets[decade].append(val)

        for decade in buckets:
            vals = buckets[decade]
            self.life_exp_by_decade[decade] = sum(vals) / len(vals)

        decades_sorted = sorted(self.life_exp_by_decade.keys())
        if len(decades_sorted) > 0:
            self.max_life_exp_decade = decades_sorted[-1]

    def _load_last_names_ranked(self):
        """
        last_names.csv columns: Decade, Rank, LastName
        rank_to_probability.csv: 1 line, 30 floats
        """
        last_path = self.data_dir + "/last_names.csv"
        rank_path = self.data_dir + "/rank_to_probability.csv"

        # Read first line as a list of probabilities (rank 1..30)
        with open(rank_path, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        probs = [float(x) for x in line.split(",") if x.strip() != ""]

        with open(last_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                decade = row["Decade"].strip()
                rank = int(row["Rank"])
                lname = row["LastName"].strip()

                if rank < 1 or rank > len(probs):
                    continue

                weight = probs[rank - 1]
                if decade not in self.last_names_by_decade:
                    self.last_names_by_decade[decade] = []
                self.last_names_by_decade[decade].append((lname, weight))

        # Normalize weights per decade 
        for decade in self.last_names_by_decade:
            items = self.last_names_by_decade[decade]
            total = 0.0
            for _, w in items:
                total += float(w)
            if total > 0:
                new_items = []
                for name, w in items:
                    new_items.append((name, w / total))
                self.last_names_by_decade[decade] = new_items

    # ---------------- sampling ----------------

    def sample_gender(self, decade):
        # uses gender_name_probability.csv as male/female distribution per decade
        # 50/50 male/female
        return self.rng.choice(["male", "female"])


    def sample_first_name(self, decade, gender):
        """
        Use gender_name_probability.csv as probability that the first name
        matches the person's gender.
        """
        other_gender = "female" if gender == "male" else "male"

        # default if missing probabilities
        p_match = 1.0
        if decade in self.gender_probs and gender in self.gender_probs[decade]:
            p_match = float(self.gender_probs[decade][gender])

        roll = self.rng.random()

        # If roll <= p_match -> pick from same gender list, else from opposite gender list
        if roll <= p_match:
            key = (decade, gender)
        else:
            key = (decade, other_gender)

        if key in self.first_names and len(self.first_names[key]) > 0:
            return self.weighted_pick(self.first_names[key])

        # fallback if that bucket missing
        # try the other bucket
        other_key = (decade, other_gender) if key == (decade, gender) else (decade, gender)
        if other_key in self.first_names and len(self.first_names[other_key]) > 0:
            return self.weighted_pick(self.first_names[other_key])

        return "Alex"


    def sample_last_name(self, decade):
        if decade in self.last_names_by_decade and len(self.last_names_by_decade[decade]) > 0:
            return self.weighted_pick(self.last_names_by_decade[decade])

        # fallback: any decade
        for dec in self.last_names_by_decade:
            return self.weighted_pick(self.last_names_by_decade[dec])
        return "Smith"

    def get_life_expectancy_years(self, decade):
        if decade in self.life_exp_by_decade:
            return self.life_exp_by_decade[decade]
        if self.max_life_exp_decade is not None:
            return self.life_exp_by_decade[self.max_life_exp_decade]
        return 75.0

    # ---------------- create person ----------------

    def create_person(self, year_born, is_direct_descendant=False, allowed_last_names=None):
        decade = self.year_to_decade(year_born)

        gender = self.sample_gender(decade)
        first_name = self.sample_first_name(decade, gender)

        if is_direct_descendant:
            if allowed_last_names is None:
                raise ValueError("allowed_last_names required for direct descendants")
            last_name = self.rng.choice([allowed_last_names[0], allowed_last_names[1]])
        else:
            last_name = self.sample_last_name(decade)

        expected = year_born + self.get_life_expectancy_years(decade)
        jitter = self.rng.uniform(-10, 10)
        year_died = int(round(expected + jitter))
        if year_died < year_born:
            year_died = year_born

        p = Person(self.next_id, year_born, year_died, gender, first_name, last_name)
        p.is_direct_descendant = is_direct_descendant

        self.next_id += 1
        return p
