class FaceData:
    def __init__(self, check_status, result_status, person_id, image_path, embedding, age, age_accuracy, gender,
                 gender_accuracy, race, race_accuracy):
        self._check_status = check_status
        self._result_status = result_status
        self._person_id = person_id
        self._image_path = image_path
        self._embedding = embedding
        self._age = age
        self._age_accuracy = age_accuracy
        self._gender = gender
        self._gender_accuracy = gender_accuracy
        self._race = race
        self._race_accuracy = race_accuracy
        self._data_list = []

    @property
    def check_status(self):
        return self._check_status

    @property
    def result_status(self):
        return self._result_status

    @property
    def person_id(self):
        return self._person_id

    @property
    def image_path(self):
        return self._image_path

    @property
    def age(self):
        return self._age

    @property
    def age_accuracy(self):
        return self._age_accuracy

    @property
    def gender(self):
        return self._gender

    @property
    def gender_accuracy(self):
        return self._gender_accuracy

    @property
    def race(self):
        return self._race

    @property
    def race_accuracy(self):
        return self._race_accuracy

    @property
    def image_path(self):
        return self._image_path

    @property
    def embedding(self):
        return self._embedding

    @property
    def data_list(self):
        return self._data_list

    def add_data(self, check_status, result_status, person_id, age, age_accuracy, gender, gender_accuracy, race, race_accuracy, embedding, image_path):
        self._data_list.append({"check_status": check_status, "result_status": result_status, "person_id": person_id, "age": age,
                                "age_accuracy": age_accuracy, "gender": gender, "gender_accuracy": gender_accuracy,
                                "race": race, "race_accuracy": race_accuracy, "embedding": embedding,
                                "image_path": image_path})
    def print_data_list(self):
        if not self.data_list:
            print("Data List is empty.")
        else:
            print("Data List:")
            for data in self.data_list:
                print(f"  {{'embedding': {data['embedding']}, 'image_path': '{data['image_path']}'}}")

    def __repr__(self):
        data_list_str = "\n".join(
            [f"{{'embedding': {data['embedding']}, 'image_path': '{data['image_path']}'}}" for data in self.data_list])
        return f"FaceData(check_status={self.check_status}, group_id={self.person_id}, age={self.age}, " \
               f"gender={self.gender}, race='{self.race},  image_path='{self.image_path}', embedding={self.embedding}, " \
               f"data_list={data_list_str})"
