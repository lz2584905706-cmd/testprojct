CREATE DATABASE IF NOT EXISTS my_user_api DEFAULT CHARSET utf8b4;

USE my_user_api;

CREATE TABLE t_user{
     id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL,
    email       VARCHAR(100) NOT NULL UNIQUE,
    status      TINYINT      DEFAULT 1,
    create_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
};

INSERT INTO t_user (name,email,status) VALUES
('alice', 'alice@test.com', 1),
('bob',   'bob@test.com',   1),
('carol', 'carol@test.com', 0);

SELECT * FROM t_user;