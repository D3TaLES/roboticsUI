def db_info(database):
    db_dict = {
        "frontend":
            {
                "host": "mongodb://rdu230:red0xfl0w@10.33.30.17:23771/ui",
                "database": "ui"
            },
        "backend":
            {
                "host": "mongodb://rdu230:red0xfl0w@10.33.30.17:23771/backend",
                "database": "backend"
            },
        "random":
            {
                "host": "mongodb://rdu230:red0xfl0w@10.33.30.17:23771/random",
                "database": "random"
            },
        "fireworks":
            {
                "host": "mongodb://rdu230:red0xfl0w@128.163.204.75:23771/fireworks",
                "database": "fireworks"
            },
        "nlp":
            {
                "host": "mongodb://readwrite:readWritenlp@10.33.30.17:23771/nlp?retryWrites=true&w=majority",
                "database": "nlp"
            },
        "robotics_backend":
            {
                "host": "mongodb://172.19.52.224:27017/",
                "port": "27017",
                "database": "backend"
            },
    }
    return db_dict[database]
