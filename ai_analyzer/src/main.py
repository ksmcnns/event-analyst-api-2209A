
from imageOperation import readImagesFromDirectory
from vectorOperation import get_json_result_using_path_array


pathArray = readImagesFromDirectory('C:\\Users\\ksmcn\\PycharmProjects\\pythonProject\\images\\wp5')
json_result = get_json_result_using_path_array(pathArray)
print(json_result)

