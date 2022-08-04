CREATE TABLE `T_CMDB_★★★UUID★★★`
(
    ROW_ID                  VARCHAR(40),
    HOST_ID                 VARCHAR(40),
    OPERATION_ID            VARCHAR(40),
    INPUT_ORDER             INT(11),
    DATA_JSON               LONGTEXT,
    NOTE                    TEXT,
    DISUSE_FLAG             VARCHAR(1),
    LAST_UPDATE_TIMESTAMP   DATETIME(6),
    LAST_UPDATE_USER        VARCHAR(40),
    PRIMARY KEY(ROW_ID)
)ENGINE = InnoDB, CHARSET = utf8mb4, COLLATE = utf8mb4_bin, ROW_FORMAT=COMPRESSED ,KEY_BLOCK_SIZE=8;

CREATE TABLE `T_CMDB_★★★UUID★★★_JNL`
(
    JOURNAL_SEQ_NO          VARCHAR(40),
    JOURNAL_REG_DATETIME    DATETIME(6),
    JOURNAL_ACTION_CLASS    VARCHAR(8),
    ROW_ID                  VARCHAR(40),
    HOST_ID                 VARCHAR(40),
    OPERATION_ID            VARCHAR(40),
    INPUT_ORDER             INT(11),
    DATA_JSON               LONGTEXT,
    NOTE                    TEXT,
    DISUSE_FLAG             VARCHAR(1),
    LAST_UPDATE_TIMESTAMP   DATETIME(6),
    LAST_UPDATE_USER        VARCHAR(40),
    PRIMARY KEY(JOURNAL_SEQ_NO)
)ENGINE = InnoDB, CHARSET = utf8mb4, COLLATE = utf8mb4_bin, ROW_FORMAT=COMPRESSED ,KEY_BLOCK_SIZE=8;
