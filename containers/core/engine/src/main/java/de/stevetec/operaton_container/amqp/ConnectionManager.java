package de.stevetec.operaton_container.amqp;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import org.operaton.bpm.engine.MismatchingMessageCorrelationException;
import org.operaton.bpm.engine.runtime.MessageCorrelationBuilder;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.DeliverCallback;

import de.stevetec.operaton_container.amqp.ConnectionManager;

import org.operaton.bpm.engine.ProcessEngine;
import org.operaton.bpm.engine.ProcessEngineException;
import org.operaton.bpm.engine.ProcessEngines;
import org.operaton.bpm.engine.RuntimeService;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.core.type.TypeReference;


public class ConnectionManager {
    private String connectionURI;
    private AMQPClient client;
    public void initializeConnection(){
        this.client = new AMQPClient(this.connectionURI);
        client.init();
    }

	public AMQPClient getClient(){
		return this.client;
	}
    
    public void startListener(String target){
        // Get the active Process engine instance
        ProcessEngine processEngine = ProcessEngines.getDefaultProcessEngine();
		RuntimeService runtimeService = processEngine.getRuntimeService();

        // Start the AMQP inbound message recieve loop
		DeliverCallback deliverCallback = (consumerTag, delivery) -> {
			String rawJSON = new String(delivery.getBody(), StandardCharsets.UTF_8);

			ObjectMapper mapper = new ObjectMapper();
			JsonNode root;
			try{
				root = mapper.readTree(rawJSON);
			}catch(JsonParseException e){
				System.out.println(String.format("[AMQP] WARN recieved inavlid JSON payload: %s",e.getMessage()));
				return;
			}

			String pid = root.path("pid").asText(""); // Process ID to correltae with
			String messageName = root.path("messageName").asText(null); // Message ID to emit

			// extract variables
			Map<String, Object> variables = mapper.convertValue(
					root.path("processVariables"),
					new TypeReference<HashMap<String, Object>>() {
					});

			// correlate
			try{
				MessageCorrelationBuilder correlation = runtimeService.createMessageCorrelation(messageName);
				correlation.setVariables(variables);
				if (pid.length() != 0) { // correlate to PID
					correlation.processInstanceId(pid);
					correlation.correlate();
				} else { // start instance
					correlation.correlateStartMessage();
	
				}
			}catch(ProcessEngineException e){
				System.out.println(String.format("[AMQP] WARN unable to correlate message %s for PID %s: %s",messageName,pid,e.getMessage()));
			}
		};

		try {
			client.registerCallback(target, deliverCallback);
		} catch (IOException e) {
			System.out.println("[AMQP] ERROR listener failiure");
			e.printStackTrace();
		}
    }

    public ConnectionManager(String uri) {
        this.connectionURI = uri;
    }
}
