import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/api/v1/ws/topic/analyze"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Send a dummy abstract to start the session
            msg = {
                "type": "user_message",
                "abstract": "This is a test abstract that is long enough to pass the length check.",
                "language": "en"
            }
            print(f"Sending: {msg}")
            await websocket.send(json.dumps(msg))
            
            # Listen for messages
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Received: {data}")
                
                if data.get("type") == "error":
                    print("Received error!")
                    break
                    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed: {e.code} {e.reason}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
