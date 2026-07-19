package de.stevetec.operaton_container;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.operaton.connect.Connectors;
@SpringBootApplication
public class BpmnEngineCoreApplication {

	public static void main(String[] args) {
		SpringApplication.run(BpmnEngineCoreApplication.class, args);
		System.out.print(Connectors.getAvailableConnectors());
	}

}
