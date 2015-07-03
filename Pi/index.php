<html>
	<head>
		<title>Fireworks!</title>
		
		<style type="text/css">
		.fw {
			display: inline-block;
			text-align: center;
			float: left;
			width: 100px;
			height: 120px;
		}
		
		.content {
			display: inline-block;
			text-align: center;
		}
		
		.select {
			width: 64px;
			height: 64px;		
			margin: auto;
			background-color: black;
		}
		
		.current {
			color: black;
			font-weight: bolder;
			font-size: large;		
		}
		
		.status-good > .select {
			background-color: green;
		}

		.status-bad > .select {
			background-color: red;
		}

		.status-launching > .select {
			background-color: yellow;
		}

		.ident {
			position: absolute;
			font-size: 24px;
			font-weight: bold;
			text-shadow: black 0.1em 0.1em 0.2em;
			color: white;
			padding-left: 3px;
			padding-top: 1px;
		}

		.hidden {
			display: none;		
		}
		</style>
	</head>
	<body>
		<script type="text/javascript">
			var ua = window.navigator.userAgent;
			var CURID = -1;
			
			function sendCommand() {
				if (CURID == -1)
					return;
					
				var xmlHttp = new XMLHttpRequest();
				
				xmlHttp.open("GET", "serial.php?req=[L" + CURID + "]", true);
				xmlHttp.send(null);
				
				CURID = -1;
			}
			
			function getStatus() {
				var xhr = new XMLHttpRequest();
				
				xhr.onreadystatechange = function () {
					if (xhr.readyState == 4) {
						var vals = xhr.responseText.split(",");
						
						for (x = 0; x < vals.length / 2; x++) {
							var status;
							
							if (parseInt(vals[x * 2 + 1]) < 100)
								status = "bad";
							else
								status = "good";
								
							updateStatus(vals[x * 2], status, vals[x * 2 + 1]);
						}
						
					}
				}
				
				xhr.open("GET", "serial.php?req=[S]", true);
				xhr.send(null);
				setTimeout(getStatus, 10000);
			}
			
			function setCurrent(id) {
				var curNameElem = document.getElementById("currentName");
				var curStatusElem = document.getElementById("currentStatus");
				var curOhmsElem = document.getElementById("currentOhms");
				var launchButtonElem = document.getElementById("launchButton");
				var div = document.getElementById("fw" + id);
				
				curNameElem.innerHTML = div.childNodes[0].childNodes[0].innerHTML;
				curStatusElem.innerHTML = div.childNodes[0].childNodes[3].innerHTML;
				curOhmsElem.innerHTML = "(" + div.childNodes[0].childNodes[4].innerHTML + ")";
				
				CURID = id;				
			}
			
			function updateStatus(id, status, ohms) {
				var div = document.getElementById("fw" + id);
				
				if (div) {
					div.childNodes[0].className = "status-" + status;
					div.childNodes[0].childNodes[3].innerHTML = status;
					div.childNodes[0].childNodes[4].innerHTML = ohms;
				}
			}
			
			function init() {
				setTimeout(getStatus, 1000);
			}
			
			window.onload = init;
		</script>
		<div class="header" id="header">
			<table style="width: 100%;">
				<tr>
					<td style="text-align: center; valign: center; width: 50%;">
						<table>
							<tr>
								<td>
									<table>
										<tr>
											<td style="text-align: left;">
												<span id="currentName" class="current">{name goes here}</span>
											</td>
										</tr>
										<tr>
											<td style="text-align: center;">
												<span id="currentStatus">{status goes here}</span>
											</td>
										</tr>
										<tr>
											<td style="text-align: center;">
												<span id="currentOhms">{ohms goes here}</span>
											</td>
										</tr>	
									</table>
								</td>							
							</tr>	
						</table>
					</td>
					<td style="text-align: center; valign: center; width: 50%;" rowspan="3">
						<button onclick="javascript:sendCommand();">Fire!</button>
					</td>
				</tr>
			</table>

		</div>
		<hr/>
		<div class="content" id="content">
		<?php
			$file_handle = fopen("fw2015.txt", "r");
			
			while(!feof($file_handle)) {
				$line = trim(fgets($file_handle));
				
				$split = explode(",", $line);
				
				if (count($split) == 2)
					echo generateDiv($split[0], $split[1]);
			}
			
			fclose($file_handle);
			
			function generateDiv($num, $id) {
				$div = '<div class="fw" id="fw' . $id . '">';
				$div .= '<div>';
				$div .= '<span class="ident">' . $num . '</span>';
				$div .= '<div class="select" onclick="javascript:setCurrent(\'' . $id . '\')"></div>';
				$div .= '<br/>';
				$div .= '<div class="hidden" id="fw' . $id . '-status"></div>';
				$div .= '<div class="hidden" id="fw' . $id . '-ohms"></div>';
				$div .= '</div>';
				$div .= '</div>';
				
				return $div;		
			}
		?>
		</div>
	</body>
</html>
