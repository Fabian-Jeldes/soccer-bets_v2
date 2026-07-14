import redis.asyncio as aioredis
from app.config import settings
import asyncio

class MockPubSub:
    def __init__(self, client):
        self.client = client
        self.queue = asyncio.Queue()
        
    async def subscribe(self, channel):
        self.client.subscribers.setdefault(channel, []).append(self)
        
    async def unsubscribe(self, channel):
        if self in self.client.subscribers.get(channel, []):
            self.client.subscribers[channel].remove(self)
            
    async def listen(self):
        while True:
            msg = await self.queue.get()
            yield msg
            
    async def close(self):
        pass

class MockRedis:
    def __init__(self):
        self.zsets = {}
        self.streams = {}
        self.subscribers = {}
        
    async def xadd(self, stream_name, fields, maxlen=None):
        self.streams.setdefault(stream_name, []).append(fields)
        
    async def xread(self, streams, count=None, block=None):
        result = []
        for stream_name, last_id in streams.items():
            msgs = self.streams.get(stream_name, [])
            try:
                if last_id == "$":
                    idx = len(msgs)
                else:
                    if "-" in str(last_id):
                        idx = int(str(last_id).split("-")[0]) + 1
                    else:
                        idx = int(last_id) + 1
            except ValueError:
                idx = 0
            
            if idx >= len(msgs) and block:
                # Simular tiempo de espera block (en ms)
                await asyncio.sleep(block / 1000.0 if block > 0 else 0.1)
                msgs = self.streams.get(stream_name, [])
            
            stream_result = []
            limit = count if count else len(msgs)
            added = 0
            for i in range(idx, len(msgs)):
                if added >= limit:
                    break
                msg_id = f"{i}-0"
                stream_result.append((msg_id, msgs[i]))
                added += 1
            
            if stream_result:
                result.append((stream_name, stream_result))
        return result
        
    async def zadd(self, zset_key, mapping):
        zset = self.zsets.setdefault(zset_key, {})
        for member, score in mapping.items():
            zset[member] = score
            
    async def zrem(self, zset_key, member):
        zset = self.zsets.get(zset_key, {})
        if member in zset:
            del zset[member]
            
    async def zrevrange(self, zset_key, start, stop):
        zset = self.zsets.get(zset_key, {})
        # Ordenar por puntaje (ROI) de mayor a menor
        sorted_items = sorted(zset.items(), key=lambda x: x[1], reverse=True)
        return [member for member, score in sorted_items]

    async def zrange(self, zset_key, start, stop):
        zset = self.zsets.get(zset_key, {})
        # Ordenar por puntaje (ROI) de menor a mayor
        sorted_items = sorted(zset.items(), key=lambda x: x[1])
        return [member for member, score in sorted_items]
        
    async def publish(self, channel, message):
        subs = self.subscribers.get(channel, [])
        for sub in subs:
            await sub.queue.put({"type": "message", "channel": channel, "data": message})
            
    def pubsub(self):
        return MockPubSub(self)

    async def aclose(self):
        pass


class RedisManager:
    def __init__(self):
        self.pool = None
        self.client = None
        self.is_mock = False

    async def connect(self):
        try:
            self.pool = aioredis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2.0 # Timeout corto para no colgar el arranque
            )
            self.client = aioredis.Redis(connection_pool=self.pool)
            # Validar conexión real
            await self.client.ping()
            self.is_mock = False
            print("Conexión exitosa a Redis Server real.")
        except Exception as e:
            self.is_mock = True
            self.client = MockRedis()
            print(f"ADVERTENCIA: No se pudo conectar a Redis en {settings.REDIS_HOST}:{settings.REDIS_PORT} ({e}).")
            print("Iniciando con fallback: SIMULADOR DE REDIS EN MEMORIA.")
        return self.client

    async def disconnect(self):
        if not self.is_mock:
            if self.client:
                await self.client.aclose()
            if self.pool:
                await self.pool.disconnect()

redis_manager = RedisManager()
