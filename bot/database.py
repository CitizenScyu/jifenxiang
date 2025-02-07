import sqlite3
import json
from datetime import datetime
import logging
from config import ALLOWED_GROUPS

class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.create_tables()
        self.init_allowed_groups()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # 用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points REAL DEFAULT 0,
            last_checkin DATE,
            invite_code TEXT UNIQUE,
            invited_by INTEGER,
            joined_date DATETIME,
            last_message_time DATETIME
        )''')

        # 群组设置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_settings (
            group_id INTEGER PRIMARY KEY,
            min_words INTEGER DEFAULT 5,
            points_per_word REAL DEFAULT 0.1,
            points_per_media INTEGER DEFAULT 1,
            daily_points INTEGER DEFAULT 5,
            invite_points INTEGER DEFAULT 10,
            is_allowed BOOLEAN DEFAULT 0
        )''')

        # 抽奖表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lotteries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            creator_id INTEGER,
            points_required INTEGER,
            keyword TEXT,
            end_time DATETIME,
            max_participants INTEGER,
            status TEXT,
            winners_count INTEGER,
            prize_description TEXT,
            prize_type TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        # 抽奖参与者表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lottery_participants (
            lottery_id INTEGER,
            user_id INTEGER,
            username TEXT,
            join_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_winner BOOLEAN DEFAULT 0,
            FOREIGN KEY (lottery_id) REFERENCES lotteries(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')

        # 邀请记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS invite_history (
            inviter_id INTEGER,
            invited_id INTEGER,
            group_id INTEGER,
            invite_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            points_awarded INTEGER,
            FOREIGN KEY (inviter_id) REFERENCES users(user_id),
            FOREIGN KEY (invited_id) REFERENCES users(user_id)
        )''')

        self.conn.commit()

    def init_allowed_groups(self):
        cursor = self.conn.cursor()
        for group_id in ALLOWED_GROUPS:
            cursor.execute('''
                INSERT OR REPLACE INTO group_settings 
                (group_id, is_allowed) 
                VALUES (?, 1)
            ''', (group_id,))
        self.conn.commit()

    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

    def add_user(self, user_id, username):
        if not self.get_user(user_id):
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO users (user_id, username, joined_date) VALUES (?, ?, ?)',
                (user_id, username, datetime.now())
            )
            self.conn.commit()

    def update_points(self, user_id, points_delta):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE users SET points = points + ? WHERE user_id = ?',
            (points_delta, user_id)
        )
        self.conn.commit()

    def get_group_settings(self, group_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM group_settings WHERE group_id = ?', (group_id,))
        return cursor.fetchone()

    def set_group_settings(self, group_id, settings):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO group_settings 
            (group_id, min_words, points_per_word, points_per_media, daily_points, invite_points, is_allowed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            group_id,
            settings.get('min_words', 5),
            settings.get('points_per_word', 0.1),
            settings.get('points_per_media', 1),
            settings.get('daily_points', 5),
            settings.get('invite_points', 10),
            1 if group_id in ALLOWED_GROUPS else 0
        ))
        self.conn.commit()

    def is_group_allowed(self, group_id):
        return group_id in ALLOWED_GROUPS

    def create_lottery(self, group_id, creator_id, points_required, keyword, end_time, 
                      max_participants, winners_count, prize_description, prize_type="normal"):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO lotteries 
            (group_id, creator_id, points_required, keyword, end_time, max_participants, 
             status, winners_count, prize_description, prize_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            group_id, creator_id, points_required, keyword, end_time, max_participants,
            'active', winners_count, prize_description, prize_type
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_lottery(self, lottery_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM lotteries WHERE id = ?', (lottery_id,))
        return cursor.fetchone()

    def get_active_lotteries(self, group_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM lotteries WHERE group_id = ? AND status = "active"',
            (group_id,)
        )
        return cursor.fetchall()

    def join_lottery(self, lottery_id, user_id, username):
        cursor = self.conn.cursor()
        # 检查是否已经参与
        cursor.execute(
            'SELECT * FROM lottery_participants WHERE lottery_id = ? AND user_id = ?',
            (lottery_id, user_id)
        )
        if cursor.fetchone():
            return False
            
        cursor.execute(
            'INSERT INTO lottery_participants (lottery_id, user_id, username) VALUES (?, ?, ?)',
            (lottery_id, user_id, username)
        )
        self.conn.commit()
        return True

    def export_data(self):
        cursor = self.conn.cursor()
        data = {
            'users': [],
            'group_settings': [],
            'lotteries': [],
            'lottery_participants': [],
            'invite_history': []
        }
        
        for table in data.keys():
            cursor.execute(f'SELECT * FROM {table}')
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            data[table] = [dict(zip(columns, row)) for row in rows]
            
        return data

    def import_data(self, data):
        cursor = self.conn.cursor()
        for table, rows in data.items():
            if not rows:
                continue
                
            columns = rows[0].keys()
            placeholders = ','.join(['?' for _ in columns])
            column_names = ','.join(columns)
            
            for row in rows:
                values = tuple(row.values())
                cursor.execute(
                    f'INSERT OR REPLACE INTO {table} ({column_names}) VALUES ({placeholders})',
                    values
                )
        
        self.conn.commit()

    def update_user_message_time(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE users SET last_message_time = ? WHERE user_id = ?',
            (datetime.now(), user_id)
        )
        self.conn.commit()