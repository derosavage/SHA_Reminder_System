import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class LocalDatabase {
  static Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('sha_reminder.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDB,
    );
  }

  Future _createDB(Database db, int version) async {
    // Penalty Calculations table
    await db.execute('''
      CREATE TABLE penalty_calculations (
        id TEXT PRIMARY KEY,
        missed_months INTEGER,
        monthly_contribution REAL,
        penalty_amount REAL,
        total_amount_due REAL,
        breakdown_json TEXT,
        calculation_date TEXT,
        is_synced INTEGER DEFAULT 0
      )
    ''');

    // Transactions table
    await db.execute('''
      CREATE TABLE transactions (
        id TEXT PRIMARY KEY,
        amount REAL,
        reference TEXT,
        status TEXT,
        created_at TEXT
      )
    ''');
  }

  Future<void> close() async {
    final db = _database;
    if (db != null) {
      await db.close();
    }
  }
}

final localDatabaseProvider = Provider<LocalDatabase>((ref) {
  return LocalDatabase();
});
