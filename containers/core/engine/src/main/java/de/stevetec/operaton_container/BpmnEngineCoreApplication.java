package de.stevetec.operaton_container;

import java.io.IOException;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import de.stevetec.operaton_container.amqp.AMQPClientProvider;

@SpringBootApplication
public class BpmnEngineCoreApplication {

	public static void main(String[] args) {

		// Try to connect to AMQP Broker
		String brokerURI = System.getenv("AMQP_HOST");

		AMQPClientProvider.createProvider("rabbit", brokerURI);
		AMQPClientProvider.getProvider("rabbit").initializeConnection();

		// Boot up Operaton engine
		SpringApplication.run(BpmnEngineCoreApplication.class, args);

		// Register the AMQP listener loop to enable inbound messages via AMQP
		AMQPClientProvider.getProvider("rabbit").startListener("amqp-connector-engine");
	}

}
