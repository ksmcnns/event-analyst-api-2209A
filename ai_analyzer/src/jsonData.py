class jsonData:
    def __init__(self, person_id, age, gender, race):
        self._person_id = person_id
        self._age = age
        self._gender = gender
        self._race = race
        self._data_list = []

    @property
    def person_id(self):
        return self._person_id

    @property
    def age(self):
        return self._age

    @property
    def gender(self):
        return self._gender

    @property
    def race(self):
        return self._race

    @property
    def data_list(self):
        return self._data_list

    def add_data(self, person_id, age, gender, race):
        self._data_list.append({
            "person_id": person_id,
            "age": age,
            "gender": gender,
            "race": race
        })

    def print_data_list(self):
        if not self.data_list:
            print("Data List is empty.")
        else:
            print("Data List:")
            for data in self.data_list:
                print(f"  {{'person_id': {data['person_id']}, 'age': {data['age']}, 'gender': {data['gender']}, 'race': {data['race']}}}")

    def __repr__(self):
        data_list_str = "\n".join(
            [f"{{'person_id': {data['person_id']}, 'age': {data['age']}, 'gender': {data['gender']}, 'race': {data['race']}}}" for data in self.data_list])
        return f"jsonData(person_id={self.person_id}, age={self.age}, gender={self.gender}, race={self.race}, data_list={data_list_str})"