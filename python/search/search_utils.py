from fuzzywuzzy import fuzz
from datetime import datetime

def search_dict_match(metadata, thresh=0.75, **query):
    for key, value in query.items():
        if value is None:
            continue
        if key == "content" or key == "filename" or key == "custom_filetype":
            if key == "custom_filetype":
                key = "filetype"
            score = fuzz.partial_ratio(value.lower(), metadata[key].lower())
            if score < thresh:
                return False
        elif key == "after":
            created_at = datetime.fromisoformat(metadata['created_at'])
            created_at = created_at.replace(tzinfo=None)
            if created_at < value:
                return False
        elif key == "before":
            created_at = datetime.fromisoformat(metadata['created_at'])
            created_at = created_at.replace(tzinfo=None)
            if created_at > value:
                return False
        elif key == "author" or key == "channel":
            if metadata[key + "_id"] != value.id:
                return False
        elif key == "filetype":
            filetype = metadata['content_type']
            if filetype is None:
                value = value[value.index('/') + 1:]
                filetype = metadata['filetype']
            if filetype == "jpeg" or filetype == "jpg":
                filetype = "jpg"
            if value == "jpeg" or value == "jpg":
                value = "jpg"
            if value == 'image' or value == 'audio':
                if value not in filetype:
                    return False
            else:
                if value != filetype:
                    return False
    return True
