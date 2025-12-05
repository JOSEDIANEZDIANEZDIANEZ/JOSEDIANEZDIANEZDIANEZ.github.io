const titulo_del_juego = "REPRODUCCIÓN DE LAS PLANTAS";

const preguntas = [
   { 
    pregunta: "¿QUÉ TRES TIPOS DE REPRODUCCIÓN TIENEN LAS PLANTAS?", 
    respuesta: "Asesual,sexual y alternante", 
    palabrasclave: "asexual,gametos,esporas,yemas,clones,idénticos" 
  },
  { 
    pregunta: "REPRODUCCIÓN ASEXUAL,DEFINICIÓN", 
    respuesta: "No intervienen gametos. Un nuevo individuo se origina a partir de esporas, yemas o una parte de la planta madre. Los descendientes son genéticamente idénticos a su progenitor (clones).", 
    palabrasclave: "asexual,gametos,esporas,yemas,clones,idénticos" 
  },

  { 
    pregunta: "REPRODUCCIÓN SEXUAL,DEFINICIÓN", 
    respuesta: "Requiere la unión de gametos (el polen masculino y el óvulo femenino) mediante un proceso de fecundación. De esta unión surge un cigoto que se desarrolla en una nueva planta con variabilidad genética. Es propia de gimnospermas y angiospermas.", 
    palabrasclave: "sexual,gametos,polen,óvulo,fecundación,cigoto,variabilidad" 
  },

  { 
    pregunta: "REPRODUCCIÓN ALTERNANTE,DEFINICIÓN", 
    respuesta: "El ciclo vital de la planta alterna entre dos formas distintas: el gametofito, que se reproduce sexualmente por gametos, y el esporofito, que se reproduce asexualmente mediante esporas. Es característica de musgos y helechos.", 
    palabrasclave: "alternante,gametofito,esporofito,musgos,helechos,ciclo" 
  },
 { 
    pregunta: "¿CUÁLES SON LOS DOS TIPOS DE REPRODUCCIÓN ASEXUAL?", 
    respuesta: "La esporulación y la multiplicación vegetativa", 
    palabrasclave: "asexual,gametos,esporas,yemas,clones,idénticos" 
  },
  { 
    pregunta: "ESPORULACIÓN,DEFINICIÓN", 
    respuesta: "Consiste en la formación de un nuevo individuo a partir de esporas, que son células asexuales especializadas. Estas esporas se producen en órganos específicos denominados esporangios. Una vez liberadas, las esporas caen al suelo y germinan.", 
    palabrasclave: "esporulación,esporas,esporangios,germinación,asexual" 
  },

  { 
    pregunta: "MULTIPLICACIÓN VEGETATIVA,DEFINICIÓN", 
    respuesta: "Es un proceso mediante el cual un nuevo individuo se forma a partir del desarrollo de una parte de la planta madre, como una yema del tallo.", 
    palabrasclave: "multiplicación,vegetativa,yema,tallo,planta madre" 
  },
{ 
    pregunta: "CUÁLES SON LAS CUATRO FORMAS DE MULTIPLICACIÓN VEGETATIVA", 
    respuesta: "El bulbo,tuberculos,espolones y los rizomas.", 
    palabrasclave: "multiplicación,vegetativa,yema,tallo,planta madre" 
  },

  { 
    pregunta: "BULBOS,CARACTERÍSTICAS", 
    respuesta: "Son tallos subterráneos con hojas carnosas que acumulan nutrientes. Un ejemplo clásico es la cebolla.", 
    palabrasclave: "bulbos,subterráneos,hojas carnosas,nutrientes,cebolla" 
  },

  { 
    pregunta: "TUBÉRCULOS,CARACTERÍSTICAS", 
    respuesta: "Se trata de tallos subterráneos que almacenan sustancias. El ejemplo más conocido es la patata.", 
    palabrasclave: "tubérculos,subterráneos,almacenan,patata" 
  },

  { 
    pregunta: "ESTOLONES,CARACTERÍSTICAS", 
    respuesta: "Son tallos que pueden desarrollar raíces y formar una nueva planta. Este mecanismo es visible en el trébol.", 
    palabrasclave: "estolones,tallos,raíces,trébol" 
  },

  { 
    pregunta: "RIZOMAS,CARACTERÍSTICAS", 
    respuesta: "Consisten en tallos subterráneos a partir de los que crecen nuevas plantas. El lirio se reproduce de esta manera.", 
    palabrasclave: "rizomas,subterráneos,nuevas plantas,lirio" 
  },

  { 
    pregunta: "REPRODUCCIÓN ALTERNANTE,IMPORTANCIA DE LA HUMEDAD", 
    respuesta: "La humedad es crucial porque el agua es un vehículo indispensable para el desplazamiento de los gametos masculinos hasta los femeninos, sin el cual la fecundación no sería posible.", 
    palabrasclave: "humedad,agua,gametos,desplazamiento,fecundación" 
  },
   { 
    pregunta: "DIME DOS EJEMPLOS CON CICLO DE REPRODUCCIÓN ALTERNANTE", 
    respuesta: "Los musgos y los helechos", 
    palabrasclave: "musgos,gametofito,esporofito,gametos,esporas,dominante" 
  },


  { 
    pregunta: "MUSGOS,CICLO DE REPRODUCCIÓN", 
    respuesta: "La forma dominante y más visible es el gametofito, que produce los gametos. Tras la fecundación, se desarrolla el esporofito, que depende del gametofito para nutrirse y forma esporas que darán lugar a nuevos gametofitos.", 
    palabrasclave: "musgos,gametofito,esporofito,gametos,esporas,dominante" 
  },

  { 
    pregunta: "HELECHOS,CICLO DE REPRODUCCIÓN", 
    respuesta: "La forma dominante es el esporofito. Produce esporas en los esporangios agrupados en soros. La espora germina y da lugar al gametofito (prótalo), que desarrolla gametos. La fecundación da lugar a un cigoto que se convierte en nuevo esporofito.", 
    palabrasclave: "helechos,esporofito,soros,prótalo,gametofito,ciclo" 
  },

  { 
    pregunta: "FLOR,DEFINICIÓN Y FUNCIÓN", 
    respuesta: "Es la innovación evolutiva clave de las espermatofitas. Funciona como el contenedor de los órganos sexuales de la planta, donde se producen los gametos necesarios para la fecundación.", 
    palabrasclave: "flor,órganos sexuales,gametos,fecundación,espermatofitas" 
  },

  { 
    pregunta: "GIMNOSPERMAS,CARACTERÍSTICAS DE LAS FLORES", 
    respuesta: "Presentan flores simples y unisexuales (masculinas o femeninas). Se agrupan en inflorescencias llamadas conos o piñas. El óvulo se encuentra desnudo, sin la protección de un ovario.", 
    palabrasclave: "gimnospermas,unisexuales,conos,piñas,óvulo desnudo" 
  },

  { 
    pregunta: "ANGIOSPERMAS,PARTES DE LA FLOR", 
    respuesta: "Corola (pétalos), cáliz (sépalos protectores), estambres (órgano masculino con filamento y antera), carpelo (órgano femenino con estigma, estilo y ovario) y pedúnculo (une flor al tallo).", 
    palabrasclave: "angiospermas,corola,cáliz,estambres,carpelo,pedúnculo" 
  },

  { 
    pregunta: "ESTAMBRES,ESTRUCTURA Y FUNCIÓN", 
    respuesta: "Es el órgano masculino. Cada estambre consta de un filamento que sostiene la antera. En la antera se producen los granos de polen, que contienen el gameto masculino.", 
    palabrasclave: "estambres,filamento,antera,polen,gameto masculino" 
  },

  { 
    pregunta: "CARPELO,ESTRUCTURA Y FUNCIÓN", 
    respuesta: "Es el órgano femenino. Se divide en tres partes: el estigma (superficie receptora del polen), el estilo (conducto conector) y el ovario (contiene los óvulos con el gameto femenino).", 
    palabrasclave: "carpelo,estigma,estilo,ovario,óvulos,femenino" 
  },
{ 
    pregunta: "ETAPAS DE LA REPRODUCCIÓN SEXUAL", 
    respuesta: "Formación del polen-Polinización-Fecundación-Formación de la semilla-Formación del fruto-Germinación", 
    palabrasclave: "carpelo,estigma,estilo,ovario,óvulos,femenino" 
  },
  { 
    pregunta: "POLINIZACIÓN,DEFINICIÓN", 
    respuesta: "Es el transporte del grano de polen desde el estambre hasta el carpelo. Requiere agentes polinizadores como el viento, el agua o animales como los insectos. En gimnospermas siempre es por el viento.", 
    palabrasclave: "polinización,polen,estambre,carpelo,viento,insectos" 
  },

  { 
    pregunta: "TIPOS DE POLINIZACIÓN", 
    respuesta: "Polinización cruzada: el polen llega a una flor de otra planta. Polinización autógama: el polen fecunda una flor de la misma planta.", 
    palabrasclave: "cruzada,autógama,misma planta,otra planta" 
  },

  { 
    pregunta: "FECUNDACIÓN EN PLANTAS,DEFINICIÓN", 
    respuesta: "Consiste en la fusión del gameto masculino con el gameto femenino contenido en el óvulo. Esta unión da lugar a una célula llamada cigoto. En angiospermas, el polen desarrolla un tubo polínico para alcanzar el óvulo.", 
    palabrasclave: "fecundación,fusión,gametos,cigoto,tubo polínico" 
  },

  { 
    pregunta: "SEMILLA,FORMACIÓN Y ESTRUCTURA", 
    respuesta: "Tras la fecundación, el óvulo se transforma en la semilla. Contiene el embrión (futuro de la planta) y sustancias de reserva para nutrirlo. En gimnospermas se llama piñón y no está protegida por un fruto.", 
    palabrasclave: "semilla,óvulo,embrión,sustancias de reserva,piñón" 
  },

  { 
    pregunta: "FRUTO,FORMACIÓN Y FUNCIÓN", 
    respuesta: "Ocurre exclusivamente en angiospermas. El ovario de la flor se transforma en el fruto, cuya función es proteger la semilla y facilitar su dispersión. Hay frutos carnosos (jugosos) y frutos secos (cubierta dura).", 
    palabrasclave: "fruto,ovario,angiospermas,protección,dispersión,carnosos,secos" 
  },

  { 
    pregunta: "GERMINACIÓN,DEFINICIÓN", 
    respuesta: "La semilla se desarrolla para dar lugar a una planta independiente.", 
    palabrasclave: "germinación,semilla,desarrollo,planta independiente" 
  },

  { 
    pregunta: "¿QUÉ DIFERENCIA HAY ENTRE GAMETOFITO Y ESPOROFITO?", 
    respuesta: "El gametofito se reproduce sexualmente mediante gametos, mientras que el esporofito se reproduce asexualmente mediante esporas. Son dos formas distintas que alternan en el ciclo vital de musgos y helechos.", 
    palabrasclave: "gametofito,esporofito,gametos,esporas,diferencia" 
  },

  { 
    pregunta: "¿EN QUÉ SE DIFERENCIAN LAS FLORES DE GIMNOSPERMAS Y ANGIOSPERMAS?", 
    respuesta: "Las gimnospermas tienen flores simples y unisexuales con óvulo desnudo. Las angiospermas tienen flores más complejas, pueden ser hermafroditas, y el óvulo está protegido dentro del ovario del carpelo.", 
    palabrasclave: "gimnospermas,angiospermas,unisexuales,hermafroditas,óvulo,diferencia" 
  }
];