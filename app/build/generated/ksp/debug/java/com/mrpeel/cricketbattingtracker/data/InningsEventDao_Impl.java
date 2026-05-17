package com.mrpeel.cricketbattingtracker.data;

import android.database.Cursor;
import android.os.CancellationSignal;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.room.CoroutinesRoom;
import androidx.room.EntityInsertionAdapter;
import androidx.room.RoomDatabase;
import androidx.room.RoomSQLiteQuery;
import androidx.room.util.CursorUtil;
import androidx.room.util.DBUtil;
import androidx.sqlite.db.SupportSQLiteStatement;
import java.lang.Class;
import java.lang.Exception;
import java.lang.Float;
import java.lang.Long;
import java.lang.Object;
import java.lang.Override;
import java.lang.String;
import java.lang.SuppressWarnings;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Callable;
import javax.annotation.processing.Generated;
import kotlin.Unit;
import kotlin.coroutines.Continuation;
import kotlinx.coroutines.flow.Flow;

@Generated("androidx.room.RoomProcessor")
@SuppressWarnings({"unchecked", "deprecation"})
public final class InningsEventDao_Impl implements InningsEventDao {
  private final RoomDatabase __db;

  private final EntityInsertionAdapter<InningsEvent> __insertionAdapterOfInningsEvent;

  private final EntityInsertionAdapter<HeartRateEvent> __insertionAdapterOfHeartRateEvent;

  public InningsEventDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
    this.__insertionAdapterOfInningsEvent = new EntityInsertionAdapter<InningsEvent>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "INSERT OR ABORT INTO `innings_events` (`id`,`inningsId`,`timestamp`,`description`,`batSpeed`,`impactForce`,`impactTimeMs`,`distanceRun`,`shotType`,`efficiency`,`backliftAngle`,`followThroughAngle`,`wristRollDeg`,`location`) VALUES (nullif(?, 0),?,?,?,?,?,?,?,?,?,?,?,?,?)";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final InningsEvent entity) {
        statement.bindLong(1, entity.getId());
        statement.bindLong(2, entity.getInningsId());
        statement.bindLong(3, entity.getTimestamp());
        statement.bindString(4, entity.getDescription());
        if (entity.getBatSpeed() == null) {
          statement.bindNull(5);
        } else {
          statement.bindDouble(5, entity.getBatSpeed());
        }
        if (entity.getImpactForce() == null) {
          statement.bindNull(6);
        } else {
          statement.bindDouble(6, entity.getImpactForce());
        }
        if (entity.getImpactTimeMs() == null) {
          statement.bindNull(7);
        } else {
          statement.bindLong(7, entity.getImpactTimeMs());
        }
        if (entity.getDistanceRun() == null) {
          statement.bindNull(8);
        } else {
          statement.bindDouble(8, entity.getDistanceRun());
        }
        if (entity.getShotType() == null) {
          statement.bindNull(9);
        } else {
          statement.bindString(9, entity.getShotType());
        }
        if (entity.getEfficiency() == null) {
          statement.bindNull(10);
        } else {
          statement.bindDouble(10, entity.getEfficiency());
        }
        if (entity.getBackliftAngle() == null) {
          statement.bindNull(11);
        } else {
          statement.bindDouble(11, entity.getBackliftAngle());
        }
        if (entity.getFollowThroughAngle() == null) {
          statement.bindNull(12);
        } else {
          statement.bindDouble(12, entity.getFollowThroughAngle());
        }
        if (entity.getWristRollDeg() == null) {
          statement.bindNull(13);
        } else {
          statement.bindDouble(13, entity.getWristRollDeg());
        }
        if (entity.getLocation() == null) {
          statement.bindNull(14);
        } else {
          statement.bindString(14, entity.getLocation());
        }
      }
    };
    this.__insertionAdapterOfHeartRateEvent = new EntityInsertionAdapter<HeartRateEvent>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "INSERT OR ABORT INTO `heart_rate_events` (`id`,`inningsId`,`timestamp`,`beatsPerMinute`) VALUES (nullif(?, 0),?,?,?)";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final HeartRateEvent entity) {
        statement.bindLong(1, entity.getId());
        statement.bindLong(2, entity.getInningsId());
        statement.bindLong(3, entity.getTimestamp());
        statement.bindLong(4, entity.getBeatsPerMinute());
      }
    };
  }

  @Override
  public Object insertEvent(final InningsEvent event,
      final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        __db.beginTransaction();
        try {
          __insertionAdapterOfInningsEvent.insert(event);
          __db.setTransactionSuccessful();
          return Unit.INSTANCE;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Object insertHeartRate(final HeartRateEvent hrEvent,
      final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        __db.beginTransaction();
        try {
          __insertionAdapterOfHeartRateEvent.insert(hrEvent);
          __db.setTransactionSuccessful();
          return Unit.INSTANCE;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Flow<List<InningsEvent>> getTimelineForInnings(final long inningsId) {
    final String _sql = "SELECT * FROM innings_events WHERE inningsId = ? ORDER BY timestamp ASC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    _statement.bindLong(_argIndex, inningsId);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"innings_events"}, new Callable<List<InningsEvent>>() {
      @Override
      @NonNull
      public List<InningsEvent> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfInningsId = CursorUtil.getColumnIndexOrThrow(_cursor, "inningsId");
          final int _cursorIndexOfTimestamp = CursorUtil.getColumnIndexOrThrow(_cursor, "timestamp");
          final int _cursorIndexOfDescription = CursorUtil.getColumnIndexOrThrow(_cursor, "description");
          final int _cursorIndexOfBatSpeed = CursorUtil.getColumnIndexOrThrow(_cursor, "batSpeed");
          final int _cursorIndexOfImpactForce = CursorUtil.getColumnIndexOrThrow(_cursor, "impactForce");
          final int _cursorIndexOfImpactTimeMs = CursorUtil.getColumnIndexOrThrow(_cursor, "impactTimeMs");
          final int _cursorIndexOfDistanceRun = CursorUtil.getColumnIndexOrThrow(_cursor, "distanceRun");
          final int _cursorIndexOfShotType = CursorUtil.getColumnIndexOrThrow(_cursor, "shotType");
          final int _cursorIndexOfEfficiency = CursorUtil.getColumnIndexOrThrow(_cursor, "efficiency");
          final int _cursorIndexOfBackliftAngle = CursorUtil.getColumnIndexOrThrow(_cursor, "backliftAngle");
          final int _cursorIndexOfFollowThroughAngle = CursorUtil.getColumnIndexOrThrow(_cursor, "followThroughAngle");
          final int _cursorIndexOfWristRollDeg = CursorUtil.getColumnIndexOrThrow(_cursor, "wristRollDeg");
          final int _cursorIndexOfLocation = CursorUtil.getColumnIndexOrThrow(_cursor, "location");
          final List<InningsEvent> _result = new ArrayList<InningsEvent>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final InningsEvent _item;
            final int _tmpId;
            _tmpId = _cursor.getInt(_cursorIndexOfId);
            final long _tmpInningsId;
            _tmpInningsId = _cursor.getLong(_cursorIndexOfInningsId);
            final long _tmpTimestamp;
            _tmpTimestamp = _cursor.getLong(_cursorIndexOfTimestamp);
            final String _tmpDescription;
            _tmpDescription = _cursor.getString(_cursorIndexOfDescription);
            final Float _tmpBatSpeed;
            if (_cursor.isNull(_cursorIndexOfBatSpeed)) {
              _tmpBatSpeed = null;
            } else {
              _tmpBatSpeed = _cursor.getFloat(_cursorIndexOfBatSpeed);
            }
            final Float _tmpImpactForce;
            if (_cursor.isNull(_cursorIndexOfImpactForce)) {
              _tmpImpactForce = null;
            } else {
              _tmpImpactForce = _cursor.getFloat(_cursorIndexOfImpactForce);
            }
            final Long _tmpImpactTimeMs;
            if (_cursor.isNull(_cursorIndexOfImpactTimeMs)) {
              _tmpImpactTimeMs = null;
            } else {
              _tmpImpactTimeMs = _cursor.getLong(_cursorIndexOfImpactTimeMs);
            }
            final Float _tmpDistanceRun;
            if (_cursor.isNull(_cursorIndexOfDistanceRun)) {
              _tmpDistanceRun = null;
            } else {
              _tmpDistanceRun = _cursor.getFloat(_cursorIndexOfDistanceRun);
            }
            final String _tmpShotType;
            if (_cursor.isNull(_cursorIndexOfShotType)) {
              _tmpShotType = null;
            } else {
              _tmpShotType = _cursor.getString(_cursorIndexOfShotType);
            }
            final Float _tmpEfficiency;
            if (_cursor.isNull(_cursorIndexOfEfficiency)) {
              _tmpEfficiency = null;
            } else {
              _tmpEfficiency = _cursor.getFloat(_cursorIndexOfEfficiency);
            }
            final Float _tmpBackliftAngle;
            if (_cursor.isNull(_cursorIndexOfBackliftAngle)) {
              _tmpBackliftAngle = null;
            } else {
              _tmpBackliftAngle = _cursor.getFloat(_cursorIndexOfBackliftAngle);
            }
            final Float _tmpFollowThroughAngle;
            if (_cursor.isNull(_cursorIndexOfFollowThroughAngle)) {
              _tmpFollowThroughAngle = null;
            } else {
              _tmpFollowThroughAngle = _cursor.getFloat(_cursorIndexOfFollowThroughAngle);
            }
            final Float _tmpWristRollDeg;
            if (_cursor.isNull(_cursorIndexOfWristRollDeg)) {
              _tmpWristRollDeg = null;
            } else {
              _tmpWristRollDeg = _cursor.getFloat(_cursorIndexOfWristRollDeg);
            }
            final String _tmpLocation;
            if (_cursor.isNull(_cursorIndexOfLocation)) {
              _tmpLocation = null;
            } else {
              _tmpLocation = _cursor.getString(_cursorIndexOfLocation);
            }
            _item = new InningsEvent(_tmpId,_tmpInningsId,_tmpTimestamp,_tmpDescription,_tmpBatSpeed,_tmpImpactForce,_tmpImpactTimeMs,_tmpDistanceRun,_tmpShotType,_tmpEfficiency,_tmpBackliftAngle,_tmpFollowThroughAngle,_tmpWristRollDeg,_tmpLocation);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Object getTimelineForInningsListSync(final long inningsId,
      final Continuation<? super List<InningsEvent>> $completion) {
    final String _sql = "SELECT * FROM innings_events WHERE inningsId = ? ORDER BY timestamp ASC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    _statement.bindLong(_argIndex, inningsId);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<InningsEvent>>() {
      @Override
      @NonNull
      public List<InningsEvent> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfInningsId = CursorUtil.getColumnIndexOrThrow(_cursor, "inningsId");
          final int _cursorIndexOfTimestamp = CursorUtil.getColumnIndexOrThrow(_cursor, "timestamp");
          final int _cursorIndexOfDescription = CursorUtil.getColumnIndexOrThrow(_cursor, "description");
          final int _cursorIndexOfBatSpeed = CursorUtil.getColumnIndexOrThrow(_cursor, "batSpeed");
          final int _cursorIndexOfImpactForce = CursorUtil.getColumnIndexOrThrow(_cursor, "impactForce");
          final int _cursorIndexOfImpactTimeMs = CursorUtil.getColumnIndexOrThrow(_cursor, "impactTimeMs");
          final int _cursorIndexOfDistanceRun = CursorUtil.getColumnIndexOrThrow(_cursor, "distanceRun");
          final int _cursorIndexOfShotType = CursorUtil.getColumnIndexOrThrow(_cursor, "shotType");
          final int _cursorIndexOfEfficiency = CursorUtil.getColumnIndexOrThrow(_cursor, "efficiency");
          final int _cursorIndexOfBackliftAngle = CursorUtil.getColumnIndexOrThrow(_cursor, "backliftAngle");
          final int _cursorIndexOfFollowThroughAngle = CursorUtil.getColumnIndexOrThrow(_cursor, "followThroughAngle");
          final int _cursorIndexOfWristRollDeg = CursorUtil.getColumnIndexOrThrow(_cursor, "wristRollDeg");
          final int _cursorIndexOfLocation = CursorUtil.getColumnIndexOrThrow(_cursor, "location");
          final List<InningsEvent> _result = new ArrayList<InningsEvent>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final InningsEvent _item;
            final int _tmpId;
            _tmpId = _cursor.getInt(_cursorIndexOfId);
            final long _tmpInningsId;
            _tmpInningsId = _cursor.getLong(_cursorIndexOfInningsId);
            final long _tmpTimestamp;
            _tmpTimestamp = _cursor.getLong(_cursorIndexOfTimestamp);
            final String _tmpDescription;
            _tmpDescription = _cursor.getString(_cursorIndexOfDescription);
            final Float _tmpBatSpeed;
            if (_cursor.isNull(_cursorIndexOfBatSpeed)) {
              _tmpBatSpeed = null;
            } else {
              _tmpBatSpeed = _cursor.getFloat(_cursorIndexOfBatSpeed);
            }
            final Float _tmpImpactForce;
            if (_cursor.isNull(_cursorIndexOfImpactForce)) {
              _tmpImpactForce = null;
            } else {
              _tmpImpactForce = _cursor.getFloat(_cursorIndexOfImpactForce);
            }
            final Long _tmpImpactTimeMs;
            if (_cursor.isNull(_cursorIndexOfImpactTimeMs)) {
              _tmpImpactTimeMs = null;
            } else {
              _tmpImpactTimeMs = _cursor.getLong(_cursorIndexOfImpactTimeMs);
            }
            final Float _tmpDistanceRun;
            if (_cursor.isNull(_cursorIndexOfDistanceRun)) {
              _tmpDistanceRun = null;
            } else {
              _tmpDistanceRun = _cursor.getFloat(_cursorIndexOfDistanceRun);
            }
            final String _tmpShotType;
            if (_cursor.isNull(_cursorIndexOfShotType)) {
              _tmpShotType = null;
            } else {
              _tmpShotType = _cursor.getString(_cursorIndexOfShotType);
            }
            final Float _tmpEfficiency;
            if (_cursor.isNull(_cursorIndexOfEfficiency)) {
              _tmpEfficiency = null;
            } else {
              _tmpEfficiency = _cursor.getFloat(_cursorIndexOfEfficiency);
            }
            final Float _tmpBackliftAngle;
            if (_cursor.isNull(_cursorIndexOfBackliftAngle)) {
              _tmpBackliftAngle = null;
            } else {
              _tmpBackliftAngle = _cursor.getFloat(_cursorIndexOfBackliftAngle);
            }
            final Float _tmpFollowThroughAngle;
            if (_cursor.isNull(_cursorIndexOfFollowThroughAngle)) {
              _tmpFollowThroughAngle = null;
            } else {
              _tmpFollowThroughAngle = _cursor.getFloat(_cursorIndexOfFollowThroughAngle);
            }
            final Float _tmpWristRollDeg;
            if (_cursor.isNull(_cursorIndexOfWristRollDeg)) {
              _tmpWristRollDeg = null;
            } else {
              _tmpWristRollDeg = _cursor.getFloat(_cursorIndexOfWristRollDeg);
            }
            final String _tmpLocation;
            if (_cursor.isNull(_cursorIndexOfLocation)) {
              _tmpLocation = null;
            } else {
              _tmpLocation = _cursor.getString(_cursorIndexOfLocation);
            }
            _item = new InningsEvent(_tmpId,_tmpInningsId,_tmpTimestamp,_tmpDescription,_tmpBatSpeed,_tmpImpactForce,_tmpImpactTimeMs,_tmpDistanceRun,_tmpShotType,_tmpEfficiency,_tmpBackliftAngle,_tmpFollowThroughAngle,_tmpWristRollDeg,_tmpLocation);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Flow<List<InningsEvent>> getAllEventsFlow() {
    final String _sql = "SELECT * FROM innings_events ORDER BY timestamp DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"innings_events"}, new Callable<List<InningsEvent>>() {
      @Override
      @NonNull
      public List<InningsEvent> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfInningsId = CursorUtil.getColumnIndexOrThrow(_cursor, "inningsId");
          final int _cursorIndexOfTimestamp = CursorUtil.getColumnIndexOrThrow(_cursor, "timestamp");
          final int _cursorIndexOfDescription = CursorUtil.getColumnIndexOrThrow(_cursor, "description");
          final int _cursorIndexOfBatSpeed = CursorUtil.getColumnIndexOrThrow(_cursor, "batSpeed");
          final int _cursorIndexOfImpactForce = CursorUtil.getColumnIndexOrThrow(_cursor, "impactForce");
          final int _cursorIndexOfImpactTimeMs = CursorUtil.getColumnIndexOrThrow(_cursor, "impactTimeMs");
          final int _cursorIndexOfDistanceRun = CursorUtil.getColumnIndexOrThrow(_cursor, "distanceRun");
          final int _cursorIndexOfShotType = CursorUtil.getColumnIndexOrThrow(_cursor, "shotType");
          final int _cursorIndexOfEfficiency = CursorUtil.getColumnIndexOrThrow(_cursor, "efficiency");
          final int _cursorIndexOfBackliftAngle = CursorUtil.getColumnIndexOrThrow(_cursor, "backliftAngle");
          final int _cursorIndexOfFollowThroughAngle = CursorUtil.getColumnIndexOrThrow(_cursor, "followThroughAngle");
          final int _cursorIndexOfWristRollDeg = CursorUtil.getColumnIndexOrThrow(_cursor, "wristRollDeg");
          final int _cursorIndexOfLocation = CursorUtil.getColumnIndexOrThrow(_cursor, "location");
          final List<InningsEvent> _result = new ArrayList<InningsEvent>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final InningsEvent _item;
            final int _tmpId;
            _tmpId = _cursor.getInt(_cursorIndexOfId);
            final long _tmpInningsId;
            _tmpInningsId = _cursor.getLong(_cursorIndexOfInningsId);
            final long _tmpTimestamp;
            _tmpTimestamp = _cursor.getLong(_cursorIndexOfTimestamp);
            final String _tmpDescription;
            _tmpDescription = _cursor.getString(_cursorIndexOfDescription);
            final Float _tmpBatSpeed;
            if (_cursor.isNull(_cursorIndexOfBatSpeed)) {
              _tmpBatSpeed = null;
            } else {
              _tmpBatSpeed = _cursor.getFloat(_cursorIndexOfBatSpeed);
            }
            final Float _tmpImpactForce;
            if (_cursor.isNull(_cursorIndexOfImpactForce)) {
              _tmpImpactForce = null;
            } else {
              _tmpImpactForce = _cursor.getFloat(_cursorIndexOfImpactForce);
            }
            final Long _tmpImpactTimeMs;
            if (_cursor.isNull(_cursorIndexOfImpactTimeMs)) {
              _tmpImpactTimeMs = null;
            } else {
              _tmpImpactTimeMs = _cursor.getLong(_cursorIndexOfImpactTimeMs);
            }
            final Float _tmpDistanceRun;
            if (_cursor.isNull(_cursorIndexOfDistanceRun)) {
              _tmpDistanceRun = null;
            } else {
              _tmpDistanceRun = _cursor.getFloat(_cursorIndexOfDistanceRun);
            }
            final String _tmpShotType;
            if (_cursor.isNull(_cursorIndexOfShotType)) {
              _tmpShotType = null;
            } else {
              _tmpShotType = _cursor.getString(_cursorIndexOfShotType);
            }
            final Float _tmpEfficiency;
            if (_cursor.isNull(_cursorIndexOfEfficiency)) {
              _tmpEfficiency = null;
            } else {
              _tmpEfficiency = _cursor.getFloat(_cursorIndexOfEfficiency);
            }
            final Float _tmpBackliftAngle;
            if (_cursor.isNull(_cursorIndexOfBackliftAngle)) {
              _tmpBackliftAngle = null;
            } else {
              _tmpBackliftAngle = _cursor.getFloat(_cursorIndexOfBackliftAngle);
            }
            final Float _tmpFollowThroughAngle;
            if (_cursor.isNull(_cursorIndexOfFollowThroughAngle)) {
              _tmpFollowThroughAngle = null;
            } else {
              _tmpFollowThroughAngle = _cursor.getFloat(_cursorIndexOfFollowThroughAngle);
            }
            final Float _tmpWristRollDeg;
            if (_cursor.isNull(_cursorIndexOfWristRollDeg)) {
              _tmpWristRollDeg = null;
            } else {
              _tmpWristRollDeg = _cursor.getFloat(_cursorIndexOfWristRollDeg);
            }
            final String _tmpLocation;
            if (_cursor.isNull(_cursorIndexOfLocation)) {
              _tmpLocation = null;
            } else {
              _tmpLocation = _cursor.getString(_cursorIndexOfLocation);
            }
            _item = new InningsEvent(_tmpId,_tmpInningsId,_tmpTimestamp,_tmpDescription,_tmpBatSpeed,_tmpImpactForce,_tmpImpactTimeMs,_tmpDistanceRun,_tmpShotType,_tmpEfficiency,_tmpBackliftAngle,_tmpFollowThroughAngle,_tmpWristRollDeg,_tmpLocation);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Object getHeartRatesForInningsSync(final long inningsId,
      final Continuation<? super List<HeartRateEvent>> $completion) {
    final String _sql = "SELECT * FROM heart_rate_events WHERE inningsId = ? ORDER BY timestamp ASC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    _statement.bindLong(_argIndex, inningsId);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<HeartRateEvent>>() {
      @Override
      @NonNull
      public List<HeartRateEvent> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfInningsId = CursorUtil.getColumnIndexOrThrow(_cursor, "inningsId");
          final int _cursorIndexOfTimestamp = CursorUtil.getColumnIndexOrThrow(_cursor, "timestamp");
          final int _cursorIndexOfBeatsPerMinute = CursorUtil.getColumnIndexOrThrow(_cursor, "beatsPerMinute");
          final List<HeartRateEvent> _result = new ArrayList<HeartRateEvent>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final HeartRateEvent _item;
            final int _tmpId;
            _tmpId = _cursor.getInt(_cursorIndexOfId);
            final long _tmpInningsId;
            _tmpInningsId = _cursor.getLong(_cursorIndexOfInningsId);
            final long _tmpTimestamp;
            _tmpTimestamp = _cursor.getLong(_cursorIndexOfTimestamp);
            final long _tmpBeatsPerMinute;
            _tmpBeatsPerMinute = _cursor.getLong(_cursorIndexOfBeatsPerMinute);
            _item = new HeartRateEvent(_tmpId,_tmpInningsId,_tmpTimestamp,_tmpBeatsPerMinute);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Object getLatestInningsId(final Continuation<? super Long> $completion) {
    final String _sql = "SELECT MAX(inningsId) FROM innings_events";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<Long>() {
      @Override
      @Nullable
      public Long call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Long _result;
          if (_cursor.moveToFirst()) {
            final Long _tmp;
            if (_cursor.isNull(0)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getLong(0);
            }
            _result = _tmp;
          } else {
            _result = null;
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Flow<Long> getLatestInningsIdFlow() {
    final String _sql = "SELECT MAX(inningsId) FROM innings_events";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"innings_events"}, new Callable<Long>() {
      @Override
      @Nullable
      public Long call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Long _result;
          if (_cursor.moveToFirst()) {
            final Long _tmp;
            if (_cursor.isNull(0)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getLong(0);
            }
            _result = _tmp;
          } else {
            _result = null;
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Object getAllUniqueInningsIds(final Continuation<? super List<Long>> $completion) {
    final String _sql = "SELECT DISTINCT inningsId FROM innings_events ORDER BY inningsId DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<Long>>() {
      @Override
      @NonNull
      public List<Long> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final List<Long> _result = new ArrayList<Long>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final Long _item;
            _item = _cursor.getLong(0);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}
