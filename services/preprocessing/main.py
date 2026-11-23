from shared.common import *
app=make_app('preprocessing')
@app.post('/internal/process-once')
def process_once(limit:int=100):
    consumer=KafkaConsumer('logs.raw',bootstrap_servers=KAFKA,auto_offset_reset='earliest',enable_auto_commit=False,consumer_timeout_ms=1000,value_deserializer=lambda x:json.loads(x.decode()),group_id='logiq-preprocessor')
    done=0; p=producer()
    try:
        for msg in consumer:
            e=msg.value; raw=e.get('raw_message',e.get('message','')); ts,sev,clean=parse_line(raw)
            e['message']=clean; e['severity']=e.get('severity') or sev; e['timestamp']=e.get('timestamp') or ts; e['preprocessed_at']=datetime.now(timezone.utc).isoformat()
            p.send('logs.preprocessed',e,key=e.get('application_id')); done+=1
            if done>=limit: break
        p.flush(); consumer.commit()
    finally: consumer.close(); p.close()
    return {'processed':done}
