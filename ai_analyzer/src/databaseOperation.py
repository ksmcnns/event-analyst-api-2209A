import ast
import os
import random
import shutil

from deepface import DeepFace
from ai_analyzer.src.jsonData import jsonData
import json
import psycopg2
from collections import Counter

# TensorFlow'u CPU kullanacak şekilde ayarla
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


def jsonService():
    # Database Connection
    conn = psycopg2.connect(
        host='localhost',
        port='5433',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()

    try:
        # Sabit ırk listesi (Veritabanındaki 'race' sütunundaki değerlerle eşleşmeli)
        races = ['White', 'Black', 'Asian', 'Indian']

        # Person count
        cursor.execute("SELECT COUNT(person_id) FROM person_individuals")
        person_count = cursor.fetchone()[0]

        # Gender counts
        cursor.execute("SELECT gender, COUNT(*) FROM person_individuals GROUP BY gender")
        # fetchall() ile gelen veriyi doğrudan sözlüğe çeviriyoruz.
        # Örneğin: [('Male', 10), ('Female', 12)] -> {'Male': 10, 'Female': 12}
        raw_gender_counts = dict(cursor.fetchall())

        # JSON çıktısı için beklenen cinsiyetleri ve varsayılan 0 değerlerini sağlıyoruz.
        # Veritabanınızda 'Male' ve 'Female' stringleri kullanıldığını varsayıyorum.
        gender_counts_output = {
            "Male": raw_gender_counts.get("Male", 0),
            "Female": raw_gender_counts.get("Female", 0)
            # Eğer başka cinsiyet etiketleri de varsa buraya ekleyin.
        }

        # Race counts
        race_counts = {}
        for race_category in races: # Değişken adını 'race_category' olarak değiştirdim, iç döngü değişkeni 'race' ile çakışmayı önlemek için.
            # Parametreli sorgu kullanarak SQL enjeksiyon riskini azaltın
            cursor.execute("SELECT COUNT(*) FROM person_individuals WHERE race = %s", (race_category,))
            count = cursor.fetchone()[0]
            race_counts[race_category] = count

        # Age distribution - BURADA DÜZELTME YAPILDI
        # Sayısal yaş kodlarını (0, 1, 2, 3) string yaş aralıklarına dönüştüren eşleme
        age_code_to_string_map = {
            0: "0-10",
            1: "11-20",
            2: "21-40",
            3: "41-60" # Eğer '41-60' için 3 kullanılıyorsa
            # Eğer daha fazla yaş kategorisi varsa buraya ekleyin (örneğin 4: "61+")
        }

        # JSON çıktısında görünmesini istediğimiz tüm yaş aralıklarını ve başlangıç sayımlarını tanımla
        age_distribution_output = {
            "0-10": 0,
            "11-20": 0,
            "21-40": 0,
            "41-60": 0 # Bu da eğer 41-60 aralığınız varsa.
            # Diğer yaş aralıklarınız varsa buraya ekleyin.
        }

        cursor.execute("SELECT age FROM person_individuals")
        # fetchall() bir tuple listesi döndürür, her tuple'dan ilk elemanı (age kodu) alıyoruz.
        ages_from_db_codes = [age_tuple[0] for age_tuple in cursor.fetchall()]

        for age_code in ages_from_db_codes:
            # Veritabanından gelen sayısal kodu, karşılık gelen string yaş aralığına çevir
            age_category_string = age_code_to_string_map.get(age_code)

            if age_category_string: # Eğer age_code için geçerli bir eşleşme varsa
                # İlgili yaş aralığının sayımını artır
                age_distribution_output[age_category_string] = age_distribution_output.get(age_category_string, 0) + 1
            # else:
            #     print(f"Uyarı: Bilinmeyen yaş kodu bulundu: {age_code}")
            #     # Bilinmeyen kodları yakalamak isterseniz burada bir 'Unknown' kategorisi ekleyebilirsiniz.


        # Construct JSON
        json_data = {
            "person_count": person_count,
            "gender_counts": gender_counts_output, # Güncellenmiş cinsiyet sayımlarını kullan
            "race_counts": race_counts,
            "age_distribution": age_distribution_output # Güncellenmiş yaş dağılımını kullan
        }

        # Return JSON data
        return json.dumps(json_data)

    except Exception as e:
        print(f"Veritabanı işlemi sırasında hata oluştu: {e}")
        # Hata durumunda boş veya hata mesajı içeren bir JSON döndürebilirsiniz.
        return json.dumps({"error": str(e)})
    finally:
        # Bağlantıyı kapat
        conn.close()

def get_most_common_value(values):
    if values:
        most_common = Counter(values).most_common()
        max_count = most_common[0][1]
        max_items = [item for item, count in most_common if count == max_count]
        return max_items[0] if len(max_items) == 1 else random.choice(max_items)
    return None

def jsonOperation(db_table):
    # Database Connection
    conn = psycopg2.connect(
        host='localhost',
        port='5433',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()

    try:
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS person_individuals (
                person_id INTEGER PRIMARY KEY,
                age INTEGER,
                gender VARCHAR(10),
                race VARCHAR(50)
            );
        """)

        # Find the highest person_id value
        cursor.execute(f"SELECT MAX(person_id) FROM {db_table}")
        max_person_id = cursor.fetchone()[0]

        if max_person_id is None:
            print("No person_id found in the table.")
            return

        data = jsonData(None, None, None, None)

        for person_id in range(1, max_person_id + 1):
            # SQL query
            sql_query = f"SELECT age, gender, race FROM {db_table} WHERE person_id = %s;"
            cursor.execute(sql_query, (person_id,))
            results = cursor.fetchall()

            if results:
                ages = []
                genders = []
                races = []

                for result in results:
                    if len(result) == 3:
                        age, gender, race = result
                        if age is not None:
                            ages.append(age)
                        if gender is not None:
                            genders.append(gender)
                        if race is not None:
                            races.append(race)

                if ages:
                    average_age = int(sum(ages) / len(ages))
                else:
                    average_age = None

                majority_gender = get_most_common_value(genders)
                majority_race = get_most_common_value(races)

                data.add_data(person_id, average_age, majority_gender, majority_race)

        # Insert data into the database with conflict handling
        for entry in data.data_list:
            cursor.execute(
                """
                INSERT INTO person_individuals (person_id, age, gender, race)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (person_id) 
                DO UPDATE SET age = EXCLUDED.age, gender = EXCLUDED.gender, race = EXCLUDED.race;
                """,
                (entry['person_id'], entry['age'], entry['gender'], entry['race'])
            )

        # Commit the transaction
        conn.commit()
        print("Data inserted into the person_individuals table successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        # Close the connection
        cursor.close()
        conn.close()

def groupe_vectors(db_table):
    # Database Connection
    conn = psycopg2.connect(
        host='localhost',
        port='5433',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()

    # fetching records count of table
    records_count = get_records_count(db_table)
    i = 1
    id = 1

    while (i < records_count + 1):
        if i == 1:
            # fetching current_vector
            cursor.execute(f"SELECT embedding FROM {db_table} WHERE id = %s;", (i,))
            current_vector = cursor.fetchone()[0]

            # Use ORDER BY and LIMIT properly
            query = f"""
                SELECT id
                FROM {db_table}
                WHERE embedding <=> %s < 0.50 AND check_status = FALSE
            """
            cursor.execute(query, (current_vector,))
            rows = cursor.fetchall()

            # Update check_status and group_id for similar vectors
            update_query = f"UPDATE {db_table} SET check_status = TRUE, person_id = %s WHERE id IN %s;"
            if rows:
                cursor.execute(update_query, (id, tuple(row[0] for row in rows)))
                conn.commit()
            i += 1
        else:
            # Fetching check_status value from embeddings2
            cursor.execute(f"SELECT check_status FROM {db_table} WHERE id = %s;", (i,))
            check_status = cursor.fetchone()[0]

            if check_status == True:
                i += 1
            elif check_status == False:
                # increment id
                id += 1

                # fetching current_vector
                cursor.execute(f"SELECT embedding FROM {db_table} WHERE id = %s;", (i,))
                current_vector = cursor.fetchone()[0]

                # Use ORDER BY and LIMIT properly
                query = f"""
                    SELECT id
                    FROM {db_table}
                    WHERE embedding <=> %s < 0.50 AND check_status = FALSE
                """
                cursor.execute(query, (current_vector,))
                rows = cursor.fetchall()

                # Update check_status and group_id for similar vectors
                update_query = f"UPDATE {db_table} SET check_status = TRUE, person_id = %s WHERE id IN %s;"
                cursor.execute(update_query, (id, tuple(row[0] for row in rows)))
                conn.commit()
                i += 1
            else:
                records_count -= 1

    cursor.close()
    conn.close()
    print('vektors are grouped')
    # extract_faces()
    #analyze_faces('vector_table')
    jsonOperation('vector_table')
    json_result = jsonService()
    return json_result

def get_records_count(table_name):
    # Database connection
    conn = psycopg2.connect(
        host='localhost',
        port='5433',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    record_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return record_count

def commit_the_results(db_table, age, gender, race, record_id):
    try:
        conn = psycopg2.connect(
            host='localhost',
            port='5433',
            database='dbproject',
            user='ksmcnns',
            password='Ks.31213000',
        )
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE {db_table} SET age = %s, gender = %s, race = %s WHERE id = %s",
            (age, gender, race, record_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error committing results: {e}")
    finally:
        cursor.close()
        conn.close()

def analyze_faces(db_table):
    # Database Connection
    conn = psycopg2.connect(
        host='localhost',
        port='5433',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()

    try:
        # Toplam kayıt sayısını al
        records_count = get_records_count(db_table)

        for record_id in range(1, records_count + 1):
            # SQL query
            sql_query = f"SELECT path FROM {db_table} WHERE id = {record_id};"
            cursor.execute(sql_query)
            result = cursor.fetchone()

            # İf result not empty fetch the path
            if result:
                face_path = result[0]  # Assuming face_path is the first column in the result
                demography_result = DeepFace.analyze(face_path, enforce_detection=False)

                # demography_result bir liste ise kontrol et
                if isinstance(demography_result, list):
                    # Listeden ilgili bilgileri çıkar (gerektiğinde düzenle)
                    age = str(demography_result[0].get("age"))
                    race = str(demography_result[0].get("dominant_race"))
                    gender = str(demography_result[0].get("gender"))
                    # Parse gender_data string to a Python dictionary
                    gender_dict = ast.literal_eval(gender)
                    # Extract accuracy values for 'Man' and 'Women'
                    accuracy_man = gender_dict['Man']
                    accuracy_women = gender_dict['Woman']
                    if accuracy_women > accuracy_man:
                        gender = "Women"
                    else:
                        gender = "Man"
                    # Commit results
                    commit_the_results(db_table, age, gender, race, record_id)
                else:
                    # Eğer bir liste değilse JSON biçimine çevir
                    demography_json = json.loads(demography_result)
                    # Demografik özellikleri atama
                    age = str(demography_json["age"])
                    detected_gender = str(demography_json["gender"])
                    race = str(demography_json["dominant_race"])

                    # Extract accuracy values for 'Man' and 'Women'
                    accuracy_man = demography_json.get('accuracy_man', 0.0)
                    accuracy_women = demography_json.get('accuracy_women', 0.0)

                    if accuracy_man > accuracy_women:
                        detected_gender = "Man"
                    else:
                        detected_gender = "Women"
                    commit_the_results(db_table, age, detected_gender, race, record_id)
        print("Faces are analyzed successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the connection
        cursor.close()
        conn.close()

def reset_database_and_directory(db_host, db_port, db_name, db_user, db_password, directory_path):
    try:
        # Database Connection
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
        )
        cursor = conn.cursor()

        # Drop the tables if they exist
        cursor.execute("DROP TABLE IF EXISTS vector_table")
        cursor.execute("DROP TABLE IF EXISTS person_individuals")
        conn.commit()
        print("Tables 'vector_table' and 'person_individuals' dropped successfully.")

        # Remove all files in the directory
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)
            os.makedirs(directory_path)  # Recreate the directory after deleting it
            print(f"All files in '{directory_path}' have been deleted and the directory has been recreated.")
        else:
            print(f"The directory '{directory_path}' does not exist.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()